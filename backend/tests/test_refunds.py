"""SCRUM-31/32 manual refunds against real PostgreSQL (docs/sprint3-sepay-plan.md D12-D14).

TEST_DATABASE_URL must name a disposable database. Rows use uuid suffixes, so the file can run
on a database shared with other tests.
"""

import asyncio
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Appointment,
    AppointmentType,
    AuditLog,
    Department,
    Doctor,
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
    RefundStatus,
    UserRole,
)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
BACKEND_DIR = Path(__file__).resolve().parents[1]

ACCOUNT = {
    "bank_bin": "970448",
    "bank_name": "OCB",
    "account_number": "0123456789",
    "account_name": "  nguyen van a ",
    "reason": "Hospital cancelled my visit.",
}


@dataclass
class Seed:
    patient: int
    patient_user: int
    other_user: int
    admin: int
    doctor: int
    type: int

    def headers(self, who: str = "patient") -> dict[str, str]:
        user_id, role = {
            "patient": (self.patient_user, "PATIENT"),
            "other": (self.other_user, "PATIENT"),
            "admin": (self.admin, "ADMIN"),
        }[who]
        return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


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


def _user(role: UserRole, suffix: str, name: str) -> User:
    user = User(
        email=f"{name}-{suffix}@example.com",
        password_hash="unused",
        role=role,
        account_status=AccountStatus.ACTIVE,
    )
    if role == UserRole.PATIENT:
        user.profile = PatientProfile(full_name=f"Refund {name}")
    return user


async def seed(session: AsyncSession) -> Seed:
    suffix = uuid.uuid4().hex
    patient = _user(UserRole.PATIENT, suffix, "patient")
    other = _user(UserRole.PATIENT, suffix, "other")
    admin = _user(UserRole.ADMIN, suffix, "admin")
    specialty = Specialty(name=f"Refund-{suffix}")
    hospital = Hospital(name="Refund hospital", address="1 Test St", city="Test city")
    session.add_all([patient, other, admin, specialty, hospital])
    await session.flush()
    department = Department(name="Refund dept", hospital_id=hospital.id, specialty_id=specialty.id)
    session.add(department)
    await session.flush()
    doctor = Doctor(full_name="Refund doctor", hospital_id=hospital.id, department_id=department.id)
    type_ = AppointmentType(name=f"Paid-{suffix}", duration_minutes=20, buffer_minutes=10)
    session.add_all([doctor, type_])
    await session.commit()
    return Seed(patient.profile.id, patient.id, other.id, admin.id, doctor.id, type_.id)


@pytest.fixture
async def context(sessions):
    async with sessions() as session:
        ids = await seed(session)

    async def request_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = request_session
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield ids, client, sessions
    finally:
        app.dependency_overrides.clear()


async def make_payment(
    sessions,
    ids: Seed,
    *,
    appointment_status: AppointmentStatus = AppointmentStatus.CANCELLED,
    payment_status: PaymentStatus = PaymentStatus.PAID,
    check_in: CheckInStatus = CheckInStatus.NOT_CHECKED_IN,
) -> tuple[int, int]:
    """An appointment (past its active life, no slot held) with one payment."""
    start = datetime.now(UTC) + timedelta(days=3, minutes=uuid.uuid4().int % 10_000)
    async with sessions() as session:
        appointment = Appointment(
            booking_reference=f"RT{uuid.uuid4().hex[:10].upper()}",
            patient_id=ids.patient,
            doctor_id=ids.doctor,
            appointment_type_id=ids.type,
            start_time=start,
            end_time=start + timedelta(minutes=20),
            end_with_buffer=start + timedelta(minutes=30),
            status=appointment_status,
            check_in_status=check_in,
            fee_amount=Decimal(2000),
            currency="VND",
        )
        session.add(appointment)
        await session.flush()
        payment = Payment(
            appointment_id=appointment.id,
            amount=Decimal(2000),
            currency="VND",
            status=payment_status,
            payment_code=f"CB{uuid.uuid4().hex[:8].upper()}",
            paid_at=datetime.now(UTC) if payment_status == PaymentStatus.PAID else None,
        )
        session.add(payment)
        await session.commit()
        return appointment.id, payment.id


def request_url(payment_id: int) -> str:
    return f"/api/v1/payments/{payment_id}/refund-request"


async def detail(client, ids: Seed, appointment_id: int) -> dict:
    response = await client.get(f"/api/v1/appointments/{appointment_id}", headers=ids.headers())
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("status", [AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED])
async def test_paid_appointment_that_will_not_happen_can_request_refund(context, status):
    ids, client, sessions = context
    appointment_id, payment_id = await make_payment(sessions, ids, appointment_status=status)
    assert (await detail(client, ids, appointment_id))["can_request_refund"] is True

    response = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "PAID"
    assert body["refund_status"] == "REQUESTED"
    assert body["refund_reference"].startswith("RF") and len(body["refund_reference"]) == 10
    assert body["refund_account_name"] == "NGUYEN VAN A"
    assert body["refund_reason"] == ACCOUNT["reason"]
    assert body["refund_requested_at"] is not None
    after = await detail(client, ids, appointment_id)
    assert after["can_request_refund"] is False
    assert after["payments"][0]["refund_status"] == "REQUESTED"
    async with sessions() as session:
        actions = (
            await session.scalars(
                select(AuditLog.action).where(
                    AuditLog.entity_type == "payment", AuditLog.entity_id == str(payment_id)
                )
            )
        ).all()
        assert "payment.refund_requested" in actions
        titles = (
            await session.scalars(
                select(Notification.title).where(Notification.user_id == ids.patient_user)
            )
        ).all()
        assert "Refund requested" in titles


@pytest.mark.parametrize(
    "appointment_status,payment_status,check_in",
    [
        (AppointmentStatus.CONFIRMED, PaymentStatus.PAID, CheckInStatus.NOT_CHECKED_IN),
        (AppointmentStatus.COMPLETED, PaymentStatus.PAID, CheckInStatus.CHECKED_IN),
        (AppointmentStatus.CANCELLED, PaymentStatus.PAID, CheckInStatus.CHECKED_IN),
        (AppointmentStatus.CANCELLED, PaymentStatus.PENDING, CheckInStatus.NOT_CHECKED_IN),
        (AppointmentStatus.CANCELLED, PaymentStatus.EXPIRED, CheckInStatus.NOT_CHECKED_IN),
        (AppointmentStatus.CANCELLED, PaymentStatus.REFUNDED, CheckInStatus.NOT_CHECKED_IN),
    ],
)
async def test_refund_not_allowed(context, appointment_status, payment_status, check_in):
    ids, client, sessions = context
    _, payment_id = await make_payment(
        sessions,
        ids,
        appointment_status=appointment_status,
        payment_status=payment_status,
        check_in=check_in,
    )
    response = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "RefundNotAllowed"


async def test_only_the_owner_can_request(context):
    ids, client, sessions = context
    _, payment_id = await make_payment(sessions, ids)
    other = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers("other"))
    assert other.status_code == 404
    missing = await client.post(request_url(2_147_483_647), json=ACCOUNT, headers=ids.headers())
    assert missing.status_code == 404
    admin = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers("admin"))
    assert admin.status_code == 403
    guest = await client.post(request_url(payment_id), json=ACCOUNT)
    assert guest.status_code == 401


@pytest.mark.parametrize(
    "field,value",
    [
        ("bank_bin", "OCB"),
        ("bank_bin", "97044"),
        ("account_number", "12"),
        ("account_number", "0123 456"),
        ("account_name", " "),
        ("bank_name", ""),
    ],
)
async def test_invalid_bank_account_is_rejected(context, field, value):
    ids, client, sessions = context
    _, payment_id = await make_payment(sessions, ids)
    response = await client.post(
        request_url(payment_id), json={**ACCOUNT, field: value}, headers=ids.headers()
    )
    assert response.status_code == 422


async def test_second_request_is_rejected(context):
    ids, client, sessions = context
    _, payment_id = await make_payment(sessions, ids)
    first = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
    assert first.status_code == 200
    again = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "RefundAlreadyRequested"


async def test_concurrent_requests_only_one_wins(context):
    ids, client, sessions = context
    _, payment_id = await make_payment(sessions, ids)
    responses = await asyncio.gather(
        *[
            client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
            for _ in range(5)
        ]
    )
    assert sorted(r.status_code for r in responses) == [200, 409, 409, 409, 409]
    async with sessions() as session:
        count = len(
            (
                await session.scalars(
                    select(AuditLog.id).where(
                        AuditLog.action == "payment.refund_requested",
                        AuditLog.entity_id == str(payment_id),
                    )
                )
            ).all()
        )
    assert count == 1


async def requested(client, ids, sessions) -> tuple[int, int, dict]:
    appointment_id, payment_id = await make_payment(sessions, ids)
    response = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
    assert response.status_code == 200, response.text
    return appointment_id, payment_id, response.json()


async def test_admin_lists_requests_with_refund_qr(context):
    ids, client, sessions = context
    _, payment_id, refund = await requested(client, ids, sessions)
    response = await client.get(
        "/api/v1/admin/refunds",
        params={"refund_status": "REQUESTED", "page_size": 100},
        headers=ids.headers("admin"),
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert all(item["refund_status"] == "REQUESTED" for item in page["items"])
    item = next(i for i in page["items"] if i["id"] == payment_id)
    assert item["patient_name"] == "Refund patient"
    assert item["patient_email"].startswith("patient-")
    qr = item["refund_qr_image_url"]
    assert qr.startswith("https://img.vietqr.io/image/970448-0123456789-compact2.png?")
    assert "amount=2000" in qr and refund["refund_reference"] in qr

    unfiltered = await client.get(
        "/api/v1/admin/refunds", params={"page_size": 100}, headers=ids.headers("admin")
    )
    assert all(i["refund_status"] is not None for i in unfiltered.json()["items"])


async def test_admin_completes_refund(context):
    ids, client, sessions = context
    appointment_id, payment_id, _ = await requested(client, ids, sessions)
    url = f"/api/v1/admin/refunds/{payment_id}/complete"

    response = await client.post(url, json={"note": "FT2611071234"}, headers=ids.headers("admin"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refund_status"] == "COMPLETED" and body["status"] == "REFUNDED"
    assert body["refund_note"] == "FT2611071234" and body["refunded_at"] is not None
    after = await detail(client, ids, appointment_id)
    assert after["payment_status"] == "REFUNDED" and after["can_request_refund"] is False
    assert (await client.post(url, json={}, headers=ids.headers("admin"))).status_code == 409
    reject = await client.post(
        f"/api/v1/admin/refunds/{payment_id}/reject",
        json={"reason": "Too late"},
        headers=ids.headers("admin"),
    )
    assert reject.status_code == 409
    again = await client.post(request_url(payment_id), json=ACCOUNT, headers=ids.headers())
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "RefundAlreadyRequested"


async def test_rejected_refund_can_be_submitted_again(context):
    ids, client, sessions = context
    appointment_id, payment_id, first = await requested(client, ids, sessions)
    reject = await client.post(
        f"/api/v1/admin/refunds/{payment_id}/reject",
        json={"reason": "Account name does not match."},
        headers=ids.headers("admin"),
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["refund_status"] == "REJECTED"
    assert reject.json()["status"] == "PAID"
    after = await detail(client, ids, appointment_id)
    assert after["can_request_refund"] is True

    retry = await client.post(
        request_url(payment_id),
        json={**ACCOUNT, "account_name": "Nguyen Van B"},
        headers=ids.headers(),
    )

    assert retry.status_code == 200, retry.text
    body = retry.json()
    assert body["refund_status"] == "REQUESTED"
    assert body["refund_account_name"] == "NGUYEN VAN B"
    assert body["refund_note"] is None
    assert body["refund_reference"] != first["refund_reference"]


async def test_admin_actions_guarded(context):
    ids, client, sessions = context
    _, payment_id, _ = await requested(client, ids, sessions)
    _, untouched = await make_payment(sessions, ids)
    complete = f"/api/v1/admin/refunds/{payment_id}/complete"
    assert (await client.post(complete, json={}, headers=ids.headers())).status_code == 403
    assert (await client.get("/api/v1/admin/refunds", headers=ids.headers())).status_code == 403
    for target in (untouched, 2_147_483_647):
        response = await client.post(
            f"/api/v1/admin/refunds/{target}/complete", json={}, headers=ids.headers("admin")
        )
        assert response.status_code == 404
    short = await client.post(
        f"/api/v1/admin/refunds/{payment_id}/reject",
        json={"reason": "x"},
        headers=ids.headers("admin"),
    )
    assert short.status_code == 422
    async with sessions() as session:
        payment = await session.get(Payment, payment_id)
        assert payment.refund_status == RefundStatus.REQUESTED
