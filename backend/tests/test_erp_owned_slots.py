"""ERP-owned directory, API permissions and shared reservations on a disposable PostgreSQL DB."""

import asyncio
import copy
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, update

from app.api.deps import get_erp
from app.core.errors import ErpUnavailable
from app.integrations.erp.base import ErpAdapter, ErpBookingResult, ErpTimeoutError
from app.models import Appointment, Doctor, DoctorSlot, ErpSyncState, PatientProfile, User
from app.models.enums import AppointmentStatus
from app.schemas.appointments import AppointmentCreate
from app.schemas.integrations import ErpEvent
from app.services import booking, erp_catalog, erp_sync

from tests import test_scheduling_integration as fixtures
from tests import test_mock_erp_shared as mock_fixtures
context = fixtures.context
sessions = fixtures.sessions
migrated = fixtures.migrated
hospital = mock_fixtures.hospital

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Disposable DB required")


@pytest.fixture
async def catalog(context, sessions):
    ids, client, redis = context
    suffix = uuid.uuid4().hex[:8]
    ids.start += timedelta(days=2)
    names = {kind: f"{kind}-{suffix}" for kind in erp_catalog.MODELS}
    snapshot = {
        "hospitals": [
            {
                "id": names["hospitals"],
                "data": {"name": f"Hospital {suffix}", "address": "Test", "city": "Test"},
            }
        ],
        "specialties": [{"id": names["specialties"], "data": {"name": f"Specialty {suffix}"}}],
        "departments": [
            {
                "id": names["departments"],
                "data": {
                    "name": "Test department",
                    "hospital_id": names["hospitals"],
                    "specialty_id": names["specialties"],
                },
            }
        ],
        "doctors": [
            {
                "id": names["doctors"],
                "data": {"full_name": f"Doctor {suffix}", "department_id": names["departments"]},
            }
        ],
        "appointment_types": [
            {
                "id": names["appointment_types"],
                "data": {
                    "name": "Standard",
                    "duration_minutes": 20,
                    "fee_override": "100000",
                    "doctor_id": names["doctors"],
                },
            }
        ],
        "slots": [
            {
                "id": names["slots"],
                "doctor_id": names["doctors"],
                "start_time": ids.start.isoformat(),
                "end_time": (ids.start + timedelta(minutes=30)).isoformat(),
                "capacity": 5,
                "is_open": True,
                "version": 1,
                "booked_count": 0,
            }
        ],
    }
    erp = AsyncMock(spec=ErpAdapter)
    erp.get_catalog.side_effect = lambda: copy.deepcopy(snapshot)

    async def accept(request):
        return ErpBookingResult(
            request.booking_reference, "ERP-" + request.booking_reference, "CONFIRMED"
        )

    erp.create_booking.side_effect = accept
    async with sessions() as session:
        state = await session.get(ErpSyncState, 1)
        state.ready = True
        await session.commit()
        await erp_catalog.sync_catalog(session, erp)
        ids.doctor = (
            await session.scalar(select(Doctor).where(Doctor.erp_id == names["doctors"]))
        ).id
        from app.models import AppointmentType

        ids.type = (
            await session.scalar(
                select(AppointmentType).where(AppointmentType.erp_id == names["appointment_types"])
            )
        ).id
    from app.main import app

    app.dependency_overrides[get_erp] = lambda: erp
    try:
        yield ids, client, redis, erp, snapshot
    finally:
        async with sessions() as session:
            await session.execute(update(Appointment).where(Appointment.doctor_id == ids.doctor)
                                  .values(status=AppointmentStatus.CANCELLED))
            await session.commit()


async def offers(client, ids):
    r = await client.get(
        f"/api/v1/doctors/{ids.doctor}/availability",
        params={"date": ids.day.isoformat(), "appointment_type_id": ids.type},
    )
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "erp-slots"
    return r.json()["slots"]


async def reserve(sessions, ids, offer, erp, redis, patient_id=None):
    async with sessions() as session:
        patient = await session.get(PatientProfile, patient_id or ids.patient)
        body = AppointmentCreate(
            **ids.payload(), slot_id=offer["slot_id"], slot_version=offer["version"]
        )
        return await booking.create_appointment(session, redis, erp, patient, body, None)


@pytest.mark.parametrize(
    "entity", ["hospitals", "specialties", "departments", "doctors", "appointment-types"]
)
async def test_admin_cannot_write_erp_directory(context, entity):
    ids, client, _ = context
    for method, url in [
        ("POST", f"/api/v1/admin/{entity}"),
        ("PATCH", f"/api/v1/admin/{entity}/1"),
    ]:
        r = await client.request(method, url, json={}, headers=ids.headers())
        assert r.status_code == 403, r.text
        assert r.json()["error"]["code"] == "ErpOwnedData"


async def test_admin_cannot_write_slots(context):
    ids, client, _ = context
    for method, url in [
        ("POST", f"/api/v1/admin/doctors/{ids.doctor}/slots"),
        ("PATCH", f"/api/v1/admin/doctors/{ids.doctor}/slots/1"),
    ]:
        r = await client.request(method, url, json={}, headers=ids.headers())
        assert r.status_code == 403, r.text


async def test_sync_changes_patient_offers_without_changing_ids(catalog, sessions):
    ids, client, _, erp, snapshot = catalog
    old = (await offers(client, ids))[0]
    snapshot["slots"][0].update(capacity=7, version=2)
    snapshot["doctors"][0]["data"]["full_name"] = "Updated by ERP"
    async with sessions() as session:
        await erp_catalog.sync_catalog(session, erp)
        await erp_catalog.sync_catalog(session, erp)
    new = (await offers(client, ids))[0]
    assert new["slot_id"] == old["slot_id"]
    assert new["capacity"] == new["remaining_places"] == 7
    assert new["version"] == 2
    assert (await client.get(f"/api/v1/doctors/{ids.doctor}")).json()[
        "full_name"
    ] == "Updated by ERP"


async def test_booking_uses_erp_and_receives_completion(catalog, sessions):
    ids, client, redis, erp, snapshot = catalog
    offer = (await offers(client, ids))[0]
    appointment_id = await reserve(sessions, ids, offer, erp, redis)
    async with sessions() as session:
        appt = await session.get(Appointment, appointment_id)
        assert appt.status == AppointmentStatus.PENDING
        assert appt.payment_due_at is not None
        erp.create_booking.assert_not_awaited()
        await booking.confirm_paid_with_erp(session, erp, appt)
        await session.commit()
        request = erp.create_booking.call_args.args[0]
        assert request.slot_id == snapshot["slots"][0]["id"]
        assert request.slot_version == 1
        await session.refresh(appt)
        assert appt.status == AppointmentStatus.CONFIRMED
        event = ErpEvent(
            event_id=uuid.uuid4().hex,
            type="CHECK_IN_STATUS_CHANGED",
            booking_reference=appt.booking_reference,
            erp_booking_id=appt.erp_booking_id,
            check_in_status="CHECKED_IN",
            occurred_at=datetime.now(UTC),
        )
        assert await erp_sync.handle_event(session, redis, event) == "processed"
        event = event.model_copy(
            update={
                "event_id": uuid.uuid4().hex,
                "type": "APPOINTMENT_STATUS_CHANGED",
                "status": "COMPLETED",
            }
        )
        await erp_sync.handle_event(session, redis, event)
        await session.refresh(appt)
        assert appt.status == AppointmentStatus.COMPLETED
        assert appt.payment_due_at is None
    response = await client.post(
        f"/api/v1/appointments/{appointment_id}/review",
        json={"rating": 5},
        headers=ids.headers("PATIENT"),
    )
    assert response.status_code == 201, response.text


async def test_capacity_race_and_search_excludes_full_slot(catalog, sessions):
    ids, client, redis, erp, _ = catalog
    offer = (await offers(client, ids))[0]
    patients = []
    async with sessions() as session:
        for _ in range(8):
            user = User(email=f"{uuid.uuid4().hex}@test.local", password_hash="unused")
            user.profile = PatientProfile(full_name="Patient")
            session.add(user)
            patients.append(user)
        await session.commit()
        patients = [u.profile.id for u in patients]
    results = await asyncio.gather(
        *(reserve(sessions, ids, offer, erp, redis, p) for p in patients), return_exceptions=True
    )
    assert sum(isinstance(r, int) for r in results) == 5, results
    full_offers = await offers(client, ids)
    assert len(full_offers) == 1 and full_offers[0]["remaining_places"] == 0
    search = await client.get(
        "/api/v1/doctors",
        params={
            "available_from": ids.start.isoformat(),
            "available_to": (ids.start + timedelta(minutes=30)).isoformat(),
            "page_size": 100,
        },
    )
    assert all(d["id"] != ids.doctor for d in search.json()["items"])


async def test_failed_snapshot_rolls_back(catalog, sessions):
    ids, client, _, erp, snapshot = catalog
    old = (await offers(client, ids))[0]
    snapshot["doctors"][0]["data"]["full_name"] = "Must rollback"
    snapshot["slots"][0]["capacity"] = 0
    async with sessions() as session:
        with pytest.raises(ErpUnavailable):
            await erp_catalog.sync_catalog(session, erp)
    assert (await offers(client, ids))[0] == old
    assert (await client.get(f"/api/v1/doctors/{ids.doctor}")).json()[
        "full_name"
    ] != "Must rollback"


async def test_timeout_keeps_shared_booking_pending_and_reconciles(catalog, sessions):
    ids, client, redis, erp, _ = catalog
    erp.create_booking.side_effect = ErpTimeoutError()
    offer = (await offers(client, ids))[0]
    identifier = await reserve(sessions, ids, offer, erp, redis)
    async with sessions() as session:
        row = await session.get(Appointment, identifier)
        await booking.confirm_paid_with_erp(session, erp, row)
        assert row.status == AppointmentStatus.PENDING
        row.created_at = datetime.now(UTC) - timedelta(minutes=1)
        erp.get_booking.return_value = ErpBookingResult(
            row.booking_reference, "ERP-retry", "CONFIRMED"
        )
        await session.commit()
        await erp_sync.reconcile_pending(session, erp)
        await session.refresh(row)
        assert row.status == AppointmentStatus.CONFIRMED


async def test_cancel_releases_capacity(catalog, sessions):
    ids, client, redis, erp, _ = catalog
    offer = (await offers(client, ids))[0]
    identifier = await reserve(sessions, ids, offer, erp, redis)
    async with sessions() as session:
        row = await session.get(Appointment, identifier)
        await booking.confirm_paid_with_erp(session, erp, row)
        await session.commit()
    response = await client.post(
        f"/api/v1/appointments/{identifier}/cancel", json={}, headers=ids.headers("PATIENT")
    )
    assert response.status_code == 200, response.text
    erp.cancel_booking.assert_awaited_once()
    assert (await offers(client, ids))[0]["remaining_places"] == 5


async def test_cutover_gate_blocks_new_reservations(catalog, sessions):
    ids, client, redis, erp, _ = catalog
    offer = (await offers(client, ids))[0]
    async with sessions() as session:
        state = await session.get(ErpSyncState, 1)
        state.ready = False
        await session.commit()
    from app.core.errors import ErpUnavailable

    with pytest.raises(ErpUnavailable):
        await reserve(sessions, ids, offer, erp, redis)
    assert await offers(client, ids) == []


async def test_cutover_preserves_existing_booking_and_is_repeatable(
    context, sessions, hospital, monkeypatch
):
    ids, client, redis = context
    hospital_client, module = hospital
    import httpx

    from app.commands import erp_cutover

    ids.start += timedelta(days=3)
    async with sessions() as session:
        state = await session.get(ErpSyncState, 1)
        state.ready = False
        slot = DoctorSlot(
            doctor_id=ids.doctor,
            start_time=ids.start,
            end_time=ids.start + timedelta(minutes=30),
            end_with_buffer=ids.start + timedelta(minutes=30),
            buffer_minutes=0,
            capacity=5,
            is_open=True,
            version=1,
        )
        session.add(slot)
        await session.flush()
        deadline = datetime.now(UTC) + timedelta(minutes=10)
        appt = Appointment(
            booking_reference="CUT" + uuid.uuid4().hex[:10],
            patient_id=ids.patient,
            doctor_id=ids.doctor,
            appointment_type_id=ids.type,
            slot_id=slot.id,
            reservation_position=1,
            start_time=slot.start_time,
            end_time=slot.end_time,
            end_with_buffer=slot.end_with_buffer,
            status=AppointmentStatus.CONFIRMED,
            payment_due_at=deadline,
            fee_amount=100000,
            currency="VND",
        )
        session.add(appt)
        await session.flush()
        identifier = appt.id
        await session.commit()
    monkeypatch.setattr(erp_cutover, "SessionLocal", sessions)
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original_client(**{**kw, "transport": httpx.ASGITransport(app=module.app)}),
    )
    await erp_cutover.run(False)
    async with sessions() as session:
        row = await session.get(Appointment, identifier)
        assert row.erp_booking_id is None
    await erp_cutover.run(True)
    await erp_cutover.run(True)
    async with sessions() as session:
        row = await session.get(Appointment, identifier)
        assert row.status == AppointmentStatus.CONFIRMED
        assert row.payment_due_at == deadline
        assert row.erp_booking_id == f"ERP-MIG-{identifier}"
        assert row.slot_id == slot.id
        assert (await session.get(ErpSyncState, 1)).ready
