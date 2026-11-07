"""Manual slot API, transaction and PostgreSQL concurrency tests on a disposable DB."""

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.errors import Conflict, SlotTaken
from app.integrations.erp.base import ErpAdapter
from app.models import (
    Appointment,
    AppointmentType,
    AuditLog,
    Doctor,
    DoctorSlot,
    PatientProfile,
    Payment,
    User,
)
from app.models.enums import AppointmentStatus, CheckInStatus, PaymentStatus
from app.schemas.appointments import AppointmentCreate
from app.schemas.integrations import ErpEvent
from app.schemas.slots import SlotCreate, SlotUpdate
from app.services import booking, erp_sync, manual_slots
from tests import test_scheduling_integration as scheduling_tests

MemoryRedis = scheduling_tests.MemoryRedis
reserve = scheduling_tests.reserve
migrated = scheduling_tests.migrated
context = scheduling_tests.context
sessions = scheduling_tests.sessions

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set"
)


@pytest.fixture
async def manual(context, sessions):
    ids, client, redis = context
    ids.start += timedelta(days=2)  # Keep patient cancellation outside the existing cutoff.
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}", json={"scheduling_mode": "MANUAL"},
        headers=ids.headers(),
    )
    assert response.status_code == 200, response.text
    response = await client.post(
        f"/api/v1/admin/doctors/{ids.doctor}/slots",
        json={"start_time": ids.start.isoformat(),
              "end_time": (ids.start + timedelta(minutes=30)).isoformat(),
              "buffer_minutes": 10, "capacity": 5}, headers=ids.headers(),
    )
    assert response.status_code == 201, response.text
    try:
        yield ids, client, redis, response.json()
    finally:
        # Existing regression modules downgrade the disposable schema. Release this test's
        # shared reservations first so the legacy single-position constraint can be restored.
        async with sessions() as session:
            await session.execute(update(Appointment).where(
                Appointment.doctor_id == ids.doctor
            ).values(status=AppointmentStatus.CANCELLED))
            await session.commit()


def payload(ids, slot, **changes):
    return {**ids.payload(), "slot_id": slot["id"], "slot_version": slot["version"], **changes}


async def book(sessions, ids, slot, patient_id=None, erp=None, redis=None, key=None):
    async with sessions() as session:
        patient = await session.get(PatientProfile, patient_id or ids.patient)
        return await booking.create_appointment(
            session, redis or MemoryRedis(), erp or AsyncMock(spec=ErpAdapter), patient,
            AppointmentCreate.model_validate(payload(ids, slot)), key,
        )


async def current_offers(client, ids):
    response = await client.get(f"/api/v1/doctors/{ids.doctor}/availability", params={
        "date": ids.day.isoformat(), "appointment_type_id": ids.type,
    })
    assert response.status_code == 200, response.text
    assert response.json()["source"] == "manual-slots"
    return response.json()["slots"]


async def test_edit_unbooked_slot_buffer_and_capacity_refreshes_public_offers(manual):
    ids, client, _, slot = manual
    # Prime the patient availability cache before editing the existing slot.
    assert (await current_offers(client, ids))[0]["capacity"] == 5
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}/slots/{slot['id']}",
        json={"version": slot["version"], "start_time": slot["start_time"],
              "end_time": slot["end_time"], "buffer_minutes": 15,
              "capacity": 7, "is_open": True}, headers=ids.headers(),
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["id"] == slot["id"]
    assert updated["buffer_minutes"] == 15
    assert updated["capacity"] == 7
    offers = await current_offers(client, ids)
    assert len(offers) == 1
    assert offers[0]["slot_id"] == slot["id"]
    assert offers[0]["version"] == updated["version"]
    assert offers[0]["capacity"] == offers[0]["remaining_places"] == 7


@pytest.mark.parametrize("field,value", [
    ("capacity", 0), ("capacity", True), ("capacity", 1.5), ("capacity", None),
    ("buffer_minutes", -1), ("buffer_minutes", 121), ("buffer_minutes", False),
    ("is_open", "yes"),
])
def test_slot_input_validation(field, value):
    body = {"start_time": "2030-01-01T08:00:00+07:00",
            "end_time": "2030-01-01T08:30:00+07:00", field: value}
    with pytest.raises(ValidationError):
        SlotCreate.model_validate(body)
    with pytest.raises(ValidationError):
        SlotUpdate.model_validate({"version": 1, field: value})


@pytest.mark.parametrize("role,expected", [(None, 401), ("PATIENT", 403)])
async def test_only_admins_manage_slots(manual, role, expected):
    ids, client, _, slot = manual
    url = f"/api/v1/admin/doctors/{ids.doctor}/slots"
    headers = ids.headers(role) if role else {}
    response = await client.get(url, params={"date": ids.day.isoformat()}, headers=headers)
    assert response.status_code == expected
    response = await client.post(url, json={"start_time": slot["start_time"],
                                          "end_time": slot["end_time"]}, headers=headers)
    assert response.status_code == expected
    response = await client.patch(f"{url}/{slot['id']}", json={"version": 1, "capacity": 9},
                                  headers=headers)
    assert response.status_code == expected


async def test_manual_offers_exact_shared_interval_and_ignore_erp_window_limit(manual, sessions):
    ids, client, redis, slot = manual
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        doctor.max_appointments_per_window = 1
        doctor.erp_doctor_id = "MANUAL-" + uuid.uuid4().hex
        await session.commit()
    offers = await current_offers(client, ids)
    assert len(offers) == 1
    assert offers[0]["slot_id"] == slot["id"]
    assert offers[0]["capacity"] == offers[0]["remaining_places"] == 5
    erp = AsyncMock(spec=ErpAdapter)
    appointment_id = await book(sessions, ids, slot, erp=erp, redis=redis)
    erp.create_booking.assert_not_called()
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.status == AppointmentStatus.CONFIRMED
        assert appointment.erp_booking_id is None
        assert appointment.end_time - appointment.start_time == timedelta(minutes=30)
        assert appointment.end_with_buffer - appointment.end_time == timedelta(minutes=10)
    assert (await current_offers(client, ids))[0]["remaining_places"] == 4


async def test_five_places_allow_exactly_five_concurrent_distinct_patients(manual, sessions):
    ids, client, _, slot = manual
    patients = []
    async with sessions() as session:
        for i in range(12):
            user = User(email=f"manual-{uuid.uuid4().hex}@example.com", password_hash="unused")
            user.profile = PatientProfile(full_name=f"Patient {i}")
            session.add(user)
            patients.append(user)
        await session.commit()
        patient_ids = [user.profile.id for user in patients]

    async def attempt(patient_id):
        try:
            return await book(sessions, ids, slot, patient_id)
        except SlotTaken as exc:
            assert exc.code == "SlotFull"
            return None

    results = await asyncio.gather(*(attempt(patient_id) for patient_id in patient_ids))
    assert sum(item is not None for item in results) == 5
    assert await current_offers(client, ids) == []
    async with sessions() as session:
        positions = (await session.scalars(select(Appointment.reservation_position).where(
            Appointment.slot_id == slot["id"]
        ))).all()
        assert sorted(positions) == [1, 2, 3, 4, 5]


async def test_duplicate_patient_and_cancel_rebook(manual, sessions):
    ids, client, _, slot = manual
    first = await book(sessions, ids, slot)
    with pytest.raises(Conflict, match="already have"):
        await book(sessions, ids, slot)
    response = await client.post(f"/api/v1/appointments/{first}/cancel",
                                 json={}, headers=ids.headers("PATIENT"))
    assert response.status_code == 200, response.text
    assert (await current_offers(client, ids))[0]["remaining_places"] == 5
    second = await book(sessions, ids, slot)
    assert second != first


async def test_admin_doctor_creation_defaults_to_manual_and_cannot_enable_erp(manual, sessions):
    ids, client, _, _ = manual
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        department_id = doctor.department_id
    body = {"department_id": department_id, "full_name": "New manual doctor"}
    response = await client.post("/api/v1/admin/doctors", json=body, headers=ids.headers())
    assert response.status_code == 201, response.text
    assert response.json()["scheduling_mode"] == "MANUAL"
    response = await client.post("/api/v1/admin/doctors", json={**body, "scheduling_mode": "ERP"},
                                 headers=ids.headers())
    assert response.status_code == 422
    response = await client.patch(f"/api/v1/admin/doctors/{ids.doctor}",
                                  json={"scheduling_mode": "ERP"}, headers=ids.headers())
    assert response.status_code == 422


@pytest.mark.parametrize("delta,duration,buffer", [(-5, 30, 0), (20, 30, 0), (30, 30, 0)])
async def test_overlapping_intervals_and_buffer_are_rejected(manual, delta, duration, buffer):
    ids, client, _, _ = manual
    start = ids.start + timedelta(minutes=delta)
    response = await client.post(f"/api/v1/admin/doctors/{ids.doctor}/slots", json={
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(minutes=duration)).isoformat(),
        "buffer_minutes": buffer,
    }, headers=ids.headers())
    assert response.status_code == 409
    # Exact adjacency after the original slot's 10-minute buffer is allowed.
    start = ids.start + timedelta(minutes=40)
    response = await client.post(f"/api/v1/admin/doctors/{ids.doctor}/slots", json={
        "start_time": start.isoformat(), "end_time": (start + timedelta(minutes=30)).isoformat(),
    }, headers=ids.headers())
    assert response.status_code == 201


@pytest.mark.parametrize("kind", ["past", "cross_day", "too_short", "too_long", "seconds"])
async def test_invalid_slot_times_are_rejected(manual, kind):
    ids, client, _, _ = manual
    start, end = ids.start + timedelta(hours=5), ids.start + timedelta(hours=5, minutes=30)
    if kind == "past":
        start, end = datetime.now(UTC) - timedelta(hours=2), datetime.now(UTC) - timedelta(hours=1)
    elif kind == "cross_day":
        start = ids.start.replace(hour=16, minute=45)  # 23:45 clinic-local.
        end = start + timedelta(minutes=30)
    elif kind == "too_short":
        end = start + timedelta(minutes=4)
    elif kind == "too_long":
        end = start + timedelta(minutes=481)
    else:
        start += timedelta(seconds=1)
    response = await client.post(f"/api/v1/admin/doctors/{ids.doctor}/slots", json={
        "start_time": start.isoformat(), "end_time": end.isoformat(),
    }, headers=ids.headers())
    assert response.status_code == 422


async def test_booked_times_protected_capacity_closure_and_old_offer_conflicts(manual, sessions):
    ids, client, _, slot = manual
    appointment_id = await book(sessions, ids, slot)
    url = f"/api/v1/admin/doctors/{ids.doctor}/slots/{slot['id']}"
    response = await client.patch(url, json={"version": 1, "buffer_minutes": 0},
                                  headers=ids.headers())
    assert response.status_code == 409
    response = await client.patch(url, json={"version": 1, "capacity": 1}, headers=ids.headers())
    assert response.status_code == 200
    assert response.json()["booked_count"] == 1
    assert await current_offers(client, ids) == []
    # Patient cannot submit an old quote, even if the capacity is subsequently raised.
    response = await client.patch(url, json={"version": 2, "capacity": 5}, headers=ids.headers())
    assert response.status_code == 200
    old = await client.post("/api/v1/appointments", json=payload(ids, slot),
                            headers=ids.headers("PATIENT"))
    assert old.status_code == 409
    response = await client.patch(url, json={"version": 3, "is_open": False},
                                  headers=ids.headers())
    assert response.status_code == 200
    assert await current_offers(client, ids) == []
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.start_time == ids.start
        assert appointment.end_time == ids.start + timedelta(minutes=30)
        assert appointment.status == AppointmentStatus.CONFIRMED


async def test_lower_capacity_below_occupancy_preserves_every_booking(manual, sessions):
    ids, client, _, slot = manual
    await book(sessions, ids, slot)
    async with sessions() as session:
        user = User(email=f"extra-{uuid.uuid4().hex}@example.com", password_hash="unused")
        user.profile = PatientProfile(full_name="Another patient")
        session.add(user)
        await session.commit()
        patient_id = user.profile.id
    await book(sessions, ids, slot, patient_id)
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}/slots/{slot['id']}",
        json={"version": 1, "capacity": 1}, headers=ids.headers(),
    )
    assert response.status_code == 200
    assert response.json()["booked_count"] == 2 and response.json()["remaining_places"] == 0


async def test_mode_switch_and_patient_cannot_forge_slots(manual, sessions):
    ids, client, _, slot = manual
    missing = await client.post("/api/v1/appointments", json=ids.payload(),
                                headers=ids.headers("PATIENT"))
    assert missing.status_code == 422
    forged = await client.post("/api/v1/appointments", json=payload(ids, slot, slot_id=2147483647),
                               headers=ids.headers("PATIENT"))
    assert forged.status_code == 409
    await book(sessions, ids, slot)
    response = await client.patch(f"/api/v1/admin/doctors/{ids.doctor}",
                                  json={"scheduling_mode": "ERP"}, headers=ids.headers())
    assert response.status_code == 422


async def test_existing_erp_booking_blocks_switch_to_manual(context, sessions):
    ids, client, _ = context
    await reserve(sessions, ids)
    response = await client.patch(f"/api/v1/admin/doctors/{ids.doctor}",
                                  json={"scheduling_mode": "MANUAL"}, headers=ids.headers())
    assert response.status_code == 409


async def test_erp_sync_reconciliation_and_webhooks_ignore_manual_bookings(manual, sessions):
    ids, _, redis, slot = manual
    appointment_id = await book(sessions, ids, slot)
    erp = AsyncMock(spec=ErpAdapter)
    erp.get_schedule.return_value = []
    erp.get_booking.return_value = None
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        doctor.erp_doctor_id = f"MANUAL-{uuid.uuid4().hex}"
        await session.commit()
        erp_id = doctor.erp_doctor_id
        appointment = await session.get(Appointment, appointment_id)
        reference = appointment.booking_reference
        event = ErpEvent(event_id=uuid.uuid4().hex, type="APPOINTMENT_RESCHEDULED",
                         booking_reference=reference, start_time=ids.start + timedelta(hours=1),
                         end_time=ids.start + timedelta(hours=2), occurred_at=datetime.now(UTC))
        assert await erp_sync.handle_event(session, redis, event) == "ignored"
        assert appointment.start_time == ids.start
        await erp_sync.sync_all_schedules(session, erp)
        assert all(call.args[0] != erp_id for call in erp.get_schedule.call_args_list)
        assert await session.get(DoctorSlot, slot["id"]) is not None
        appointment.status = AppointmentStatus.PENDING
        appointment.created_at = datetime.now(UTC) - timedelta(hours=1)
        await session.commit()
        await erp_sync.reconcile_pending(session, erp)
        assert all(call.args[0] != reference for call in erp.get_booking.call_args_list)


async def test_failed_slot_save_rolls_back_settings_and_audit(manual, sessions, monkeypatch):
    ids, _, _, slot = manual
    async with sessions() as session:
        count = await session.scalar(select(func.count(AuditLog.id)))
        monkeypatch.setattr(session, "commit", AsyncMock(side_effect=SQLAlchemyError("failure")))
        with pytest.raises(Conflict, match="Previous settings remain effective"):
            await manual_slots.update(session, ids.doctor, slot["id"],
                                      SlotUpdate(version=1, capacity=7), ids.admin)
    async with sessions() as session:
        row = await session.get(DoctorSlot, slot["id"])
        assert row.capacity == 5 and row.version == 1
        assert await session.scalar(select(func.count(AuditLog.id))) == count


async def test_admin_edit_waits_for_reservation_and_protects_times(manual, sessions, monkeypatch):
    ids, _, _, slot = manual
    locked, release = asyncio.Event(), asyncio.Event()
    original = manual_slots.reserve_position

    async def pause(*args, **kwargs):
        result = await original(*args, **kwargs)
        locked.set()
        await release.wait()
        return result

    monkeypatch.setattr(manual_slots, "reserve_position", pause)
    reservation = asyncio.create_task(book(sessions, ids, slot))
    await asyncio.wait_for(locked.wait(), 5)

    async def edit():
        async with sessions() as session:
            return await manual_slots.update(session, ids.doctor, slot["id"],
                                             SlotUpdate(version=1, buffer_minutes=0), ids.admin)

    change = asyncio.create_task(edit())
    try:
        await asyncio.sleep(0.1)
        assert not change.done()
    finally:
        release.set()
    await asyncio.wait_for(reservation, 5)
    with pytest.raises(Conflict, match="Booked slot times"):
        await asyncio.wait_for(change, 5)


async def test_database_guards_positions_patients_and_slot_doctor(manual, sessions):
    ids, _, _, slot = manual
    appointment_id = await book(sessions, ids, slot)
    async with sessions() as session:
        assert await session.get(Appointment, appointment_id) is not None
        original_doctor = await session.get(Doctor, ids.doctor)
        other = Doctor(full_name="Other doctor", hospital_id=original_doctor.hospital_id,
                       department_id=original_doctor.department_id)
        user = User(email=f"raw-{uuid.uuid4().hex}@example.com", password_hash="unused")
        user.profile = PatientProfile(full_name="Raw database patient")
        session.add_all([user, other])
        await session.commit()
        patient_id, other_doctor_id = user.profile.id, other.id
        for patient, doctor, position, constraint in [
            (patient_id, ids.doctor, 1, "no_overlap"),
            (ids.patient, ids.doctor, 2, "uq_appointments_patient_active_slot"),
            (patient_id, other_doctor_id, 1, "fk_appointments_slot_doctor"),
        ]:
            session.add(Appointment(
                booking_reference=uuid.uuid4().hex[:16], patient_id=patient,
                doctor_id=doctor, appointment_type_id=ids.type, slot_id=slot["id"],
                reservation_position=position, start_time=ids.start,
                end_time=ids.start + timedelta(minutes=30),
                end_with_buffer=ids.start + timedelta(minutes=40),
                status=AppointmentStatus.CONFIRMED, fee_amount=0, currency="VND",
            ))
            with pytest.raises(IntegrityError) as exc:
                await session.commit()
            assert constraint in str(exc.value)
            await session.rollback()


async def test_manual_idempotent_retry_returns_same_confirmed_booking(manual, sessions):
    ids, _, _, slot = manual

    class IdempotentRedis(MemoryRedis):
        def __init__(self):
            super().__init__()
            self.keys = {}

        async def get(self, key):
            return self.keys.get(key)

        async def set(self, key, value, nx=False, **kwargs):
            if nx and key in self.keys:
                return False
            self.keys[key] = value
            return True

    redis = IdempotentRedis()
    first = await book(sessions, ids, slot, redis=redis, key="manual-retry")
    assert await book(sessions, ids, slot, redis=redis, key="manual-retry") == first


async def test_manual_paid_cancellation_keeps_payment_without_calling_erp(manual, sessions):
    """Sprint 3 D13: cancelling never refunds automatically; the paid payment stays PAID and
    the patient requests a refund separately."""
    ids, client, redis, slot = manual
    amount = Decimal("100000")
    async with sessions() as session:
        appointment_type = await session.get(AppointmentType, ids.type)
        appointment_type.fee_override = amount
        await session.commit()
    appointment_id = await book(sessions, ids, slot)
    reference = f"PAY-{uuid.uuid4().hex}"
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.fee_amount == amount
        payment = Payment(appointment_id=appointment_id, amount=amount, currency="VND",
                          status=PaymentStatus.PAID, payment_code=f"CB{uuid.uuid4().hex[:8]}",
                          provider_reference=reference, paid_at=datetime.now(UTC))
        session.add(payment)
        await session.commit()
        payment_id = payment.id
    erp = AsyncMock(spec=ErpAdapter)
    async with sessions() as session:
        patient = await session.get(PatientProfile, ids.patient)
        await booking.cancel_appointment(session, redis, erp, patient,
                                         appointment_id, "Test cancellation")
    erp.cancel_booking.assert_not_called()
    async with sessions() as session:
        assert (await session.get(Payment, payment_id)).status == PaymentStatus.PAID
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.status == AppointmentStatus.CANCELLED
    assert (await current_offers(client, ids))[0]["remaining_places"] == 5


async def test_checked_in_manual_booking_cannot_be_cancelled_or_refunded(manual, sessions):
    ids, client, _, slot = manual
    appointment_id = await book(sessions, ids, slot)
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        appointment.check_in_status = CheckInStatus.CHECKED_IN
        await session.commit()
    detail = await client.get(f"/api/v1/appointments/{appointment_id}",
                              headers=ids.headers("PATIENT"))
    assert detail.status_code == 200
    assert detail.json()["can_cancel"] is False
    response = await client.post(f"/api/v1/appointments/{appointment_id}/cancel",
                                 json={}, headers=ids.headers("PATIENT"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AlreadyCheckedIn"
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.status == AppointmentStatus.CONFIRMED


async def test_delayed_erp_reschedule_cannot_create_future_booking_in_manual_mode(manual, sessions):
    ids, _, redis, _ = manual
    past = ids.start - timedelta(days=6)
    async with sessions() as session:
        appointment = Appointment(
            booking_reference=uuid.uuid4().hex[:16], patient_id=ids.patient,
            doctor_id=ids.doctor, appointment_type_id=ids.type, start_time=past,
            end_time=past + timedelta(minutes=20), end_with_buffer=past + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED, fee_amount=0, currency="VND",
        )
        session.add(appointment)
        await session.commit()
        event = ErpEvent(
            event_id=uuid.uuid4().hex, type="APPOINTMENT_RESCHEDULED",
            booking_reference=appointment.booking_reference, start_time=ids.start,
            end_time=ids.start + timedelta(minutes=20), occurred_at=datetime.now(UTC),
        )
        assert await erp_sync.handle_event(session, redis, event) == "ignored"
        assert appointment.start_time == past
