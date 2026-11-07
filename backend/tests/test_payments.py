"""SCRUM-28/29 VietQR + SePay payments against real PostgreSQL (docs/sprint3-sepay-plan.md D3-D11).

Covers payment initiation, the SePay webhook (matching, wrong amount, replays, late money),
the User API poller, the payment deadline and the expiry job that releases unpaid slots.

TEST_DATABASE_URL must name a disposable database. Rows use uuid suffixes and every assertion
looks only at rows this file created, so it can share the database with other test files.
"""

import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_erp
from app.core.config import settings
from app.core.db import get_session
from app.core.redis import get_redis
from app.core.security import create_access_token, generate_booking_reference
from app.integrations.erp.base import ErpUnavailableError
from app.main import app
from app.models import (
    Appointment,
    AppointmentStatusHistory,
    AppointmentType,
    AuditLog,
    Department,
    Doctor,
    DoctorSchedule,
    Hospital,
    Notification,
    PatientProfile,
    Payment,
    Specialty,
    User,
)
from app.models.enums import (
    AccountStatus,
    AppointmentStatus,
    CheckInStatus,
    PaymentStatus,
    SchedulingMode,
    StatusSource,
    UserRole,
)
from app.services import availability, booking, payments, sepay
from app.services.sepay import BankTransfer

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
BACKEND_DIR = Path(__file__).resolve().parents[1]
KEY = "test-sepay-key"
FEE = Decimal("2000")


class MemoryRedis:
    """Just the availability-cache calls the services make."""

    def __init__(self) -> None:
        self.values: dict[str, dict[str, str]] = {}

    async def hget(self, key, field):
        return self.values.get(key, {}).get(field)

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    def pipeline(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def hset(self, key, field, value):
        self.values.setdefault(key, {})[field] = value

    def expire(self, *args):
        pass

    async def execute(self):
        pass


class StubErp:
    """Accepts every cancellation, or fails all of them while `down` is set."""

    def __init__(self) -> None:
        self.down = False
        self.cancelled: list[str] = []

    async def cancel_booking(self, erp_booking_id: str, reason: str | None) -> None:
        if self.down:
            raise ErpUnavailableError("ERP down")
        self.cancelled.append(erp_booking_id)


@dataclass
class Seed:
    patient: int
    patient_user: int
    other_user: int
    doctor: int
    paid_type: int
    free_type: int
    start: datetime

    def headers(self, user_id: int | None = None) -> dict[str, str]:
        token = create_access_token(user_id or self.patient_user, "PATIENT")
        return {"Authorization": f"Bearer {token}"}


@dataclass
class Ctx:
    ids: Seed
    client: httpx.AsyncClient
    sessions: async_sessionmaker
    redis: MemoryRedis
    erp: StubErp


@pytest.fixture(scope="module")
def migrated():
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        check=True,
    )


@pytest.fixture
async def sessions(migrated):
    engine = create_async_engine(TEST_DATABASE_URL, pool_size=10)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def seed(session: AsyncSession) -> Seed:
    suffix = uuid.uuid4().hex
    users = []
    for name in ("patient", "other"):
        user = User(
            email=f"pay-{name}-{suffix}@example.com",
            password_hash="unused",
            role=UserRole.PATIENT,
            account_status=AccountStatus.ACTIVE,
        )
        user.profile = PatientProfile(full_name=f"Pay {name}")
        users.append(user)
    specialty = Specialty(name=f"Pay-{suffix}")
    hospital = Hospital(name="Pay hospital", address="1 Pay St", city="Pay city")
    session.add_all([*users, specialty, hospital])
    await session.flush()
    department = Department(name="Pay dept", hospital_id=hospital.id, specialty_id=specialty.id)
    session.add(department)
    await session.flush()
    doctor = Doctor(
        full_name="Pay doctor",
        hospital_id=hospital.id,
        department_id=department.id,
        max_appointments_per_window=10,
        scheduling_mode=SchedulingMode.ERP,  # default is MANUAL (e2fc238)
    )
    session.add(doctor)
    await session.flush()
    paid = AppointmentType(
        name=f"Paid-{suffix}",
        duration_minutes=20,
        buffer_minutes=10,
        fee_override=FEE,
        doctor_id=doctor.id,
    )
    free = AppointmentType(
        name=f"Free-{suffix}", duration_minutes=20, buffer_minutes=10, doctor_id=doctor.id
    )
    session.add_all([paid, free])
    tomorrow = datetime.now(availability.clinic_tz()).date() + timedelta(days=2)
    start = datetime.combine(tomorrow, time(8), tzinfo=availability.clinic_tz()).astimezone(UTC)
    session.add(
        DoctorSchedule(
            doctor_id=doctor.id,
            start_time=start,
            end_time=start + timedelta(hours=4),
            max_appointments=None,
        )
    )
    await session.commit()
    return Seed(users[0].profile.id, users[0].id, users[1].id, doctor.id, paid.id, free.id, start)


@pytest.fixture
async def ctx(sessions, monkeypatch):
    monkeypatch.setattr(settings, "sepay_webhook_api_key", KEY)
    monkeypatch.setattr(settings, "sepay_api_token", "")
    async with sessions() as session:
        ids = await seed(session)
    redis, erp = MemoryRedis(), StubErp()

    async def request_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = request_session
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_erp] = lambda: erp
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield Ctx(ids, client, sessions, redis, erp)
    finally:
        app.dependency_overrides.clear()


async def make_appointment(
    ctx: Ctx,
    *,
    slot: int = 0,
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    due_in: timedelta | None = timedelta(minutes=15),
    free: bool = False,
    erp_booking_id: str | None = None,
) -> int:
    """Insert an appointment directly (slot = index of a 30-minute slot in the schedule)."""
    start = ctx.ids.start + timedelta(minutes=30 * slot)
    async with ctx.sessions() as session:
        appointment = Appointment(
            booking_reference=generate_booking_reference(),
            patient_id=ctx.ids.patient,
            doctor_id=ctx.ids.doctor,
            appointment_type_id=ctx.ids.free_type if free else ctx.ids.paid_type,
            start_time=start,
            end_time=start + timedelta(minutes=20),
            end_with_buffer=start + timedelta(minutes=30),
            status=status,
            check_in_status=CheckInStatus.NOT_CHECKED_IN,
            fee_amount=Decimal("0") if free else FEE,
            currency="VND",
            erp_booking_id=erp_booking_id,
            payment_due_at=datetime.now(UTC) + due_in if due_in is not None else None,
        )
        session.add(appointment)
        await session.commit()
        return appointment.id


async def initiate(ctx: Ctx, appointment_id: int, user_id: int | None = None) -> httpx.Response:
    return await ctx.client.post(
        f"/api/v1/appointments/{appointment_id}/payments", headers=ctx.ids.headers(user_id)
    )


async def pay_code(ctx: Ctx, appointment_id: int) -> dict:
    response = await initiate(ctx, appointment_id)
    assert response.status_code == 201, response.text
    return response.json()


async def webhook(
    ctx: Ctx,
    content: str,
    amount: int | Decimal = FEE,
    transfer_id: int | None = None,
    *,
    key: str | None = KEY,
    transfer_type: str = "in",
) -> httpx.Response:
    body = {
        "id": transfer_id or uuid.uuid4().int % 10**12,
        "gateway": "OCB",
        "transactionDate": "2026-11-07 14:30:00",
        "accountNumber": "SEPNK33418",
        "subAccount": None,
        "code": None,
        "content": content,
        "transferType": transfer_type,
        "transferAmount": int(amount),
        "accumulated": 0,
        "referenceCode": "FT123",
        "description": content,
    }
    headers = {"Authorization": f"Apikey {key}"} if key is not None else {}
    return await ctx.client.post("/api/v1/payments/sepay-webhook", json=body, headers=headers)


async def get_payment(ctx: Ctx, payment_id: int) -> dict:
    response = await ctx.client.get(f"/api/v1/payments/{payment_id}", headers=ctx.ids.headers())
    assert response.status_code == 200, response.text
    return response.json()


async def get_appointment(ctx: Ctx, appointment_id: int) -> dict:
    response = await ctx.client.get(
        f"/api/v1/appointments/{appointment_id}", headers=ctx.ids.headers()
    )
    assert response.status_code == 200, response.text
    return response.json()


async def audit_actions(ctx: Ctx, payment_id: int) -> list[str]:
    async with ctx.sessions() as session:
        rows = await session.scalars(
            select(AuditLog.action)
            .where(AuditLog.entity_type == "payment", AuditLog.entity_id == str(payment_id))
            .order_by(AuditLog.id)
        )
        return list(rows)


# --- Helpers (no database) --------------------------------------------------------------------


def test_extract_codes_normalises_content_and_sees_past_bank_prefixes(monkeypatch):
    monkeypatch.setattr(settings, "payment_code_prefix", "CB")
    assert sepay.extract_codes(None, "ck cbab12 cd34 thanh toan") == ["CBAB12CD34"]
    # "OCB" glued to the code: the first match is wrong, the real code is still a candidate.
    assert "CBAB12CD34" in sepay.extract_codes(None, "OCBCBAB12CD34")
    assert sepay.extract_codes("CBZZZZ9999", "CBAB12CD34")[0] == "CBZZZZ9999"
    assert sepay.extract_codes(None, "no code here") == []


def test_new_payment_code_shape(monkeypatch):
    monkeypatch.setattr(settings, "payment_code_prefix", "CB")
    codes = {sepay.new_payment_code() for _ in range(50)}
    assert len(codes) == 50
    assert all(len(c) == 10 and c.startswith("CB") and c[2:].isalnum() for c in codes)
    assert all(c == c.upper() for c in codes)


def test_api_key_check(monkeypatch):
    monkeypatch.setattr(settings, "sepay_webhook_api_key", "k1")
    assert sepay.check_api_key("Apikey k1")
    assert sepay.check_api_key("apikey  k1 ")
    assert not sepay.check_api_key("Apikey k2")
    assert not sepay.check_api_key("Bearer k1")
    assert not sepay.check_api_key(None)
    monkeypatch.setattr(settings, "sepay_webhook_api_key", "")
    assert not sepay.check_api_key("Apikey ")


def test_parse_local_time_is_vietnam_time():
    assert sepay.parse_local_time("2026-11-07 14:30:00") == datetime(2026, 11, 7, 7, 30, tzinfo=UTC)


# --- Payment deadline on confirmation (D6) ---------------------------------------------------


async def test_confirmation_sets_payment_deadline_only_when_a_fee_is_due(ctx):
    paid_id = await make_appointment(ctx, status=AppointmentStatus.PENDING, due_in=None)
    free_id = await make_appointment(
        ctx, slot=1, status=AppointmentStatus.PENDING, due_in=None, free=True
    )
    async with ctx.sessions() as session:
        for appointment_id in (paid_id, free_id):
            appointment = await session.get(Appointment, appointment_id)
            await booking.transition(
                session,
                appointment,
                AppointmentStatus.CONFIRMED,
                reason=None,
                source=StatusSource.ERP,
            )
        await session.commit()
        paid = await session.get(Appointment, paid_id)
        free = await session.get(Appointment, free_id)
    expected = datetime.now(UTC) + timedelta(minutes=settings.payment_hold_minutes)
    assert paid.payment_due_at is not None
    assert abs(paid.payment_due_at - expected) < timedelta(seconds=30)
    assert free.payment_due_at is None
    summary = await get_appointment(ctx, paid_id)
    assert summary["payment_due_at"] is not None and summary["can_pay"] is True


# --- Initiation (D3, D7, D11) ---------------------------------------------------------------


async def test_initiate_returns_qr_and_reuses_the_open_attempt(ctx):
    appointment_id = await make_appointment(ctx)
    first = await pay_code(ctx, appointment_id)
    assert first["status"] == "PENDING"
    assert first["payment_code"].startswith(settings.payment_code_prefix)
    assert first["payment_code"] in first["qr_image_url"]
    assert "amount=2000" in first["qr_image_url"]
    detail = await get_appointment(ctx, appointment_id)
    assert first["expires_at"] == detail["payment_due_at"]
    second = await pay_code(ctx, appointment_id)
    assert second["id"] == first["id"] and second["payment_code"] == first["payment_code"]
    async with ctx.sessions() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.appointment_id == appointment_id)
        )
    assert count == 1


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"free": True}, "PaymentNotRequired"),
        ({"status": AppointmentStatus.PENDING}, "PaymentNotAllowed"),
        ({"status": AppointmentStatus.CANCELLED}, "PaymentNotAllowed"),
        ({"due_in": timedelta(seconds=-1)}, "PaymentWindowClosed"),
    ],
)
async def test_initiate_rejections(ctx, kwargs, code):
    appointment_id = await make_appointment(ctx, **kwargs)
    response = await initiate(ctx, appointment_id)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == code


async def test_initiate_and_read_are_owner_only(ctx):
    appointment_id = await make_appointment(ctx)
    assert (await initiate(ctx, appointment_id, ctx.ids.other_user)).status_code == 404
    payment = await pay_code(ctx, appointment_id)
    response = await ctx.client.get(
        f"/api/v1/payments/{payment['id']}", headers=ctx.ids.headers(ctx.ids.other_user)
    )
    assert response.status_code == 404


async def test_legacy_appointment_without_deadline_can_pay(ctx):
    appointment_id = await make_appointment(ctx, due_in=None)
    payment = await pay_code(ctx, appointment_id)
    assert payment["expires_at"] is None


# --- Webhook (D5, D10) ------------------------------------------------------------------------


@pytest.mark.parametrize("key", [None, "wrong-key"])
async def test_webhook_rejects_missing_or_wrong_key(ctx, key):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    response = await webhook(ctx, payment["payment_code"], key=key)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "InvalidApiKey"
    assert (await get_payment(ctx, payment["id"]))["status"] == "PENDING"


async def test_matching_transfer_marks_paid(ctx):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    code = payment["payment_code"]
    spaced = f"{code[:5].lower()} {code[5:]}"
    transfer_id = uuid.uuid4().int % 10**12
    response = await webhook(ctx, f"MBVCB.123.{spaced}.CT tu 0123", transfer_id=transfer_id)
    assert response.status_code == 200 and response.json() == {"success": True}
    paid = await get_payment(ctx, payment["id"])
    assert paid["status"] == "PAID"
    assert paid["provider_reference"] == str(transfer_id)
    assert paid["paid_at"] == "2026-11-07T07:30:00Z"
    detail = await get_appointment(ctx, appointment_id)
    assert detail["payment_status"] == "PAID" and detail["can_pay"] is False
    async with ctx.sessions() as session:
        titles = list(
            await session.scalars(
                select(Notification.title).where(Notification.user_id == ctx.ids.patient_user)
            )
        )
    assert "Payment received" in titles
    again = await initiate(ctx, appointment_id)
    assert again.status_code == 409 and again.json()["error"]["code"] == "AlreadyPaid"


async def test_wrong_amount_keeps_pending_until_the_right_amount_arrives(ctx):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    await webhook(ctx, payment["payment_code"], amount=1000)
    current = await get_payment(ctx, payment["id"])
    assert current["status"] == "PENDING"
    assert "1,000" in current["failure_reason"] and "2,000" in current["failure_reason"]
    await webhook(ctx, payment["payment_code"], amount=FEE)
    current = await get_payment(ctx, payment["id"])
    assert current["status"] == "PAID" and current["failure_reason"] is None


async def test_replayed_and_second_transfers_are_ignored_once(ctx):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    code = payment["payment_code"]
    first, second = (uuid.uuid4().int % 10**12 for _ in range(2))
    for _ in range(2):
        assert (await webhook(ctx, code, transfer_id=first)).status_code == 200
    assert (await get_payment(ctx, payment["id"]))["provider_reference"] == str(first)
    for _ in range(2):  # a second, different transfer for an already paid payment
        assert (await webhook(ctx, code, transfer_id=second)).status_code == 200
    actions = await audit_actions(ctx, payment["id"])
    assert actions.count("payment.status_changed") == 1
    assert actions.count("payment.duplicate_transfer") == 1
    assert (await get_payment(ctx, payment["id"]))["provider_reference"] == str(first)


async def test_transfer_id_that_already_settled_another_payment_is_ignored(ctx):
    first = await pay_code(ctx, await make_appointment(ctx))
    second = await pay_code(ctx, await make_appointment(ctx, slot=1))
    transfer_id = uuid.uuid4().int % 10**12
    await webhook(ctx, first["payment_code"], transfer_id=transfer_id)
    response = await webhook(ctx, second["payment_code"], transfer_id=transfer_id)
    assert response.status_code == 200
    assert (await get_payment(ctx, first["id"]))["status"] == "PAID"
    assert (await get_payment(ctx, second["id"]))["status"] == "PENDING"


async def test_unmatched_and_outgoing_transfers_are_acknowledged_without_effect(ctx):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    response = await webhook(ctx, f"{settings.payment_code_prefix}00000000 unknown")
    assert response.status_code == 200 and response.json() == {"success": True}
    response = await webhook(ctx, payment["payment_code"], transfer_type="out")
    assert response.status_code == 200
    assert (await get_payment(ctx, payment["id"]))["status"] == "PENDING"


async def test_transfer_for_an_older_attempt_after_paying_a_new_one_is_not_double_paid(ctx):
    appointment_id = await make_appointment(ctx)
    old = await pay_code(ctx, appointment_id)
    async with ctx.sessions() as session:  # the first QR expired; the patient made a new one
        row = await session.get(Payment, old["id"])
        row.status = PaymentStatus.EXPIRED
        await session.commit()
    new = await pay_code(ctx, appointment_id)
    assert new["id"] != old["id"]
    await webhook(ctx, new["payment_code"])
    await webhook(ctx, old["payment_code"])
    assert (await get_payment(ctx, new["id"]))["status"] == "PAID"
    assert (await get_payment(ctx, old["id"]))["status"] == "EXPIRED"
    assert "payment.duplicate_transfer" in await audit_actions(ctx, old["id"])


# --- Expiry job (D6) and late money (D10) -----------------------------------------------------


async def test_expiry_cancels_unpaid_appointment_and_frees_the_slot(ctx):
    overdue = await make_appointment(ctx, due_in=timedelta(minutes=-2), erp_booking_id="ERP-A")
    in_grace = await make_appointment(ctx, slot=1, due_in=timedelta(seconds=-20))
    paid = await make_appointment(ctx, slot=2, due_in=timedelta(minutes=-2))
    payment = await pay_code_unchecked(ctx, overdue)
    paid_payment = await pay_code_unchecked(ctx, paid)
    await webhook(ctx, paid_payment["payment_code"])

    async with ctx.sessions() as session:
        await payments.expire_unpaid(session, ctx.redis, ctx.erp)

    detail = await get_appointment(ctx, overdue)
    assert detail["status"] == "CANCELLED"
    assert "deadline" in detail["status_reason"]
    assert (await get_payment(ctx, payment["id"]))["status"] == "EXPIRED"
    assert "ERP-A" in ctx.erp.cancelled
    async with ctx.sessions() as session:
        source = await session.scalar(
            select(AppointmentStatusHistory.source)
            .where(AppointmentStatusHistory.appointment_id == overdue)
            .order_by(AppointmentStatusHistory.id.desc())
            .limit(1)
        )
    assert source == StatusSource.SYSTEM
    assert (await get_appointment(ctx, in_grace))["status"] == "CONFIRMED"
    assert (await get_appointment(ctx, paid))["status"] == "CONFIRMED"

    response = await ctx.client.get(
        f"/api/v1/doctors/{ctx.ids.doctor}/availability",
        params={
            "date": availability.local_day(ctx.ids.start).isoformat(),
            "appointment_type_id": ctx.ids.paid_type,
        },
    )
    assert response.status_code == 200, response.text
    starts = {datetime.fromisoformat(s["start_time"]) for s in response.json()["slots"]}
    assert ctx.ids.start in starts  # released
    assert ctx.ids.start + timedelta(minutes=30) not in starts  # still held (grace)


async def pay_code_unchecked(ctx: Ctx, appointment_id: int) -> dict:
    """Create a PENDING payment even when the deadline already passed (test setup only)."""
    async with ctx.sessions() as session:
        payment = Payment(
            appointment_id=appointment_id,
            amount=FEE,
            currency="VND",
            status=PaymentStatus.PENDING,
            payment_code=sepay.new_payment_code(),
        )
        session.add(payment)
        await session.commit()
        return {"id": payment.id, "payment_code": payment.payment_code}


async def test_expiry_retries_when_the_erp_is_down(ctx):
    appointment_id = await make_appointment(
        ctx, due_in=timedelta(minutes=-5), erp_booking_id="ERP-DOWN"
    )
    ctx.erp.down = True
    async with ctx.sessions() as session:
        assert await payments.expire_unpaid(session, ctx.redis, ctx.erp) is False
    assert (await get_appointment(ctx, appointment_id))["status"] == "CONFIRMED"
    ctx.erp.down = False
    async with ctx.sessions() as session:
        await payments.expire_unpaid(session, ctx.redis, ctx.erp)
    assert (await get_appointment(ctx, appointment_id))["status"] == "CANCELLED"


async def test_late_transfer_after_expiry_still_pays_and_allows_refund(ctx):
    appointment_id = await make_appointment(ctx, due_in=timedelta(minutes=-2))
    payment = await pay_code_unchecked(ctx, appointment_id)
    async with ctx.sessions() as session:
        await payments.expire_unpaid(session, ctx.redis, ctx.erp)
    assert (await get_payment(ctx, payment["id"]))["status"] == "EXPIRED"
    await webhook(ctx, payment["payment_code"])
    assert (await get_payment(ctx, payment["id"]))["status"] == "PAID"
    detail = await get_appointment(ctx, appointment_id)
    assert detail["status"] == "CANCELLED"
    assert detail["can_request_refund"] is True


async def test_patient_cancel_expires_open_payment_and_never_refunds(ctx):
    pending_id = await make_appointment(ctx)
    pending = await pay_code(ctx, pending_id)
    paid_id = await make_appointment(ctx, slot=1)
    paid = await pay_code(ctx, paid_id)
    await webhook(ctx, paid["payment_code"])
    for appointment_id in (pending_id, paid_id):
        response = await ctx.client.post(
            f"/api/v1/appointments/{appointment_id}/cancel",
            json={"reason": "Changed plans"},
            headers=ctx.ids.headers(),
        )
        assert response.status_code == 200, response.text
    assert (await get_payment(ctx, pending["id"]))["status"] == "EXPIRED"
    assert (await get_payment(ctx, paid["id"]))["status"] == "PAID"
    assert (await get_appointment(ctx, paid_id))["can_request_refund"] is True


# --- User API poller (D5) ---------------------------------------------------------------------


async def test_poller_applies_transfers_once_and_is_idle_without_token(ctx, monkeypatch):
    appointment_id = await make_appointment(ctx)
    payment = await pay_code(ctx, appointment_id)
    calls: list[datetime] = []

    async def fake_fetch(since):
        calls.append(since)
        return [
            BankTransfer(
                id=f"poll-{payment['id']}",
                amount_in=FEE,
                transaction_content=f"IBFT {payment['payment_code']}",
                code=None,
                transaction_date=datetime.now(UTC),
            )
        ]

    monkeypatch.setattr(sepay, "fetch_transactions", fake_fetch)
    async with ctx.sessions() as session:
        assert await payments.sync_transfers(session) is True
    assert calls == []  # no token: polling is off

    monkeypatch.setattr(settings, "sepay_api_token", "token")
    for _ in range(2):
        async with ctx.sessions() as session:
            assert await payments.sync_transfers(session) is True
    assert len(calls) == 2
    assert (await get_payment(ctx, payment["id"]))["status"] == "PAID"
    assert (await audit_actions(ctx, payment["id"])).count("payment.status_changed") == 1


async def test_poller_failure_is_reported_not_raised(ctx, monkeypatch):
    appointment_id = await make_appointment(ctx)
    await pay_code(ctx, appointment_id)

    async def broken_fetch(since):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(settings, "sepay_api_token", "token")
    monkeypatch.setattr(sepay, "fetch_transactions", broken_fetch)
    async with ctx.sessions() as session:
        assert await payments.sync_transfers(session) is False
