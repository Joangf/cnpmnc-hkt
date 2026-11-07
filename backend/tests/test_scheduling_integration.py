"""SCRUM-21 API, persistence and real PostgreSQL concurrency regression tests.

TEST_DATABASE_URL must name a disposable database (the existing overlap test resets it).
"""

import asyncio
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_erp
from app.api.v1 import admin as admin_api
from app.core.db import get_session
from app.core.errors import Conflict, SlotTaken
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.integrations.erp.mock import InMemoryErpAdapter
from app.main import app
from app.models import (
    Appointment,
    AppointmentType,
    AuditLog,
    Department,
    Doctor,
    DoctorSchedule,
    Hospital,
    PatientProfile,
    Specialty,
    User,
)
from app.models.enums import AccountStatus, AppointmentStatus, SchedulingMode, UserRole
from app.schemas.admin import AppointmentTypeUpdate, DoctorUpdate
from app.schemas.appointments import AppointmentCreate
from app.services import availability, booking, erp_sync

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
BACKEND_DIR = Path(__file__).resolve().parents[1]


class MemoryRedis:
    """Only the cache methods exercised by the services; no Redis server needed."""

    def __init__(self) -> None:
        self.values: dict[str, dict[str, str]] = {}
        self.fail = False

    async def hget(self, key, field):
        if self.fail:
            raise RedisError("cache unavailable")
        return self.values.get(key, {}).get(field)

    async def delete(self, *keys):
        if self.fail:
            raise RedisError("cache unavailable")
        for key in keys:
            self.values.pop(key, None)

    def pipeline(self, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def hset(self, key, field, value):
        if not self.fail:
            self.values.setdefault(key, {})[field] = value

    def expire(self, *args):
        pass

    async def execute(self):
        if self.fail:
            raise RedisError("cache unavailable")


@dataclass
class Seed:
    doctor: int
    type: int
    extended_type: int
    patient: int
    patient_user: int
    admin: int
    specialty: int
    other_specialty: int
    start: datetime

    @property
    def day(self):
        return availability.local_day(self.start)

    def headers(self, role="ADMIN"):
        user_id = self.admin if role == "ADMIN" else self.patient_user
        return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}

    def payload(self, offset=0, type_id=None):
        return {
            "doctor_id": self.doctor,
            "appointment_type_id": type_id or self.type,
            "start_time": (self.start + timedelta(minutes=offset)).isoformat(),
        }


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
    patient = User(
        email=f"patient-{suffix}@example.com",
        password_hash="unused",
        role=UserRole.PATIENT,
        account_status=AccountStatus.ACTIVE,
    )
    patient.profile = PatientProfile(full_name="Test patient")
    admin = User(
        email=f"admin-{suffix}@example.com",
        password_hash="unused",
        role=UserRole.ADMIN,
        account_status=AccountStatus.ACTIVE,
    )
    specialty, other = Specialty(name=f"Primary-{suffix}"), Specialty(name=f"Other-{suffix}")
    hospital = Hospital(name="Test hospital", address="1 Test St", city="Test city")
    session.add_all([patient, admin, specialty, other, hospital])
    await session.flush()
    department = Department(
        name="Test department", hospital_id=hospital.id, specialty_id=specialty.id
    )
    session.add(department)
    await session.flush()
    doctor = Doctor(
        full_name="Test doctor",
        hospital_id=hospital.id,
        department_id=department.id,
        max_appointments_per_window=3,
        scheduling_mode=SchedulingMode.ERP,  # default is MANUAL (e2fc238)
    )
    standard = AppointmentType(name="Standard", duration_minutes=20, buffer_minutes=10)
    extended = AppointmentType(name="Extended", duration_minutes=30, buffer_minutes=10)
    session.add_all([doctor, standard, extended])
    await session.flush()
    tomorrow = datetime.now(availability.clinic_tz()).date() + timedelta(days=1)
    start = datetime.combine(tomorrow, time(8), tzinfo=availability.clinic_tz()).astimezone(UTC)
    session.add(
        DoctorSchedule(
            doctor_id=doctor.id,
            start_time=start,
            end_time=start + timedelta(hours=3),
            max_appointments=None,
        )
    )
    await session.commit()
    return Seed(
        doctor.id,
        standard.id,
        extended.id,
        patient.profile.id,
        patient.id,
        admin.id,
        specialty.id,
        other.id,
        start,
    )


@pytest.fixture
async def context(sessions):
    async with sessions() as session:
        ids = await seed(session)
    redis, erp = MemoryRedis(), InMemoryErpAdapter()

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
            yield ids, client, redis
    finally:
        app.dependency_overrides.clear()


async def offered(client, ids):
    response = await client.get(
        f"/api/v1/doctors/{ids.doctor}/availability",
        params={"date": ids.day.isoformat(), "appointment_type_id": ids.type},
    )
    assert response.status_code == 200, response.text
    return response.json()["slots"]


async def reserve(sessions, ids, offset=0, type_id=None):
    async with sessions() as session:
        patient = await session.get(PatientProfile, ids.patient)
        return await booking.create_appointment(
            session,
            MemoryRedis(),
            InMemoryErpAdapter(),
            patient,
            AppointmentCreate.model_validate(ids.payload(offset, type_id)),
            None,
        )


@pytest.mark.parametrize("role,expected", [(None, 401), ("PATIENT", 403)])
async def test_admin_settings_cannot_be_changed_by_guest_or_patient(context, role, expected):
    ids, client, _ = context
    for path, body in [
        (f"doctors/{ids.doctor}", {"max_appointments_per_window": 9}),
        (f"appointment-types/{ids.type}", {"duration_minutes": 40}),
    ]:
        response = await client.patch(
            f"/api/v1/admin/{path}", json=body, headers=ids.headers(role) if role else {}
        )
        assert response.status_code == expected


@pytest.mark.parametrize("value", [0, -1, None, True, 1.5, 2.0, "2"])
async def test_invalid_capacity_preserves_previous_value(context, value):
    ids, client, _ = context
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}",
        json={"max_appointments_per_window": value},
        headers=ids.headers(),
    )
    assert response.status_code == 422
    doctors = await client.get("/api/v1/admin/doctors", headers=ids.headers())
    assert (
        next(d for d in doctors.json() if d["id"] == ids.doctor)["max_appointments_per_window"] == 3
    )
    public = await client.get(f"/api/v1/doctors/{ids.doctor}")
    assert "max_appointments_per_window" not in public.json()


async def test_merged_scope_is_validated_and_failed_patch_is_atomic(context):
    ids, client, _ = context
    url = f"/api/v1/admin/appointment-types/{ids.type}"
    response = await client.patch(
        url, json={"doctor_id": ids.doctor, "specialty_id": ids.specialty}, headers=ids.headers()
    )
    assert response.status_code == 200
    response = await client.patch(
        url,
        json={"specialty_id": ids.other_specialty, "duration_minutes": 40},
        headers=ids.headers(),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ContradictoryScope"
    response = await client.get("/api/v1/admin/appointment-types", headers=ids.headers())
    current = next(t for t in response.json() if t["id"] == ids.type)
    assert current["specialty_id"] == ids.specialty and current["duration_minutes"] == 20
    response = await client.patch(url, json={"doctor_id": 2147483647}, headers=ids.headers())
    assert response.status_code == 422


async def test_concurrent_nonoverlapping_bookings_share_capacity_across_types(context, sessions):
    ids, client, _ = context
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}",
        json={"max_appointments_per_window": 1},
        headers=ids.headers(),
    )
    assert response.status_code == 200

    async def attempt(i):
        try:
            return await reserve(sessions, ids, 40 * i, ids.type if i % 2 else ids.extended_type)
        except SlotTaken:
            return None

    results = await asyncio.gather(*(attempt(i) for i in range(4)))
    assert sum(result is not None for result in results) == 1
    assert await offered(client, ids) == []
    response = await client.post(
        "/api/v1/appointments", json=ids.payload(120), headers=ids.headers("PATIENT")
    )
    assert response.status_code == 409  # Direct API calls cannot bypass a full window.


async def test_edits_preserve_intervals_and_lower_capacity_stops_offers(context, sessions):
    ids, client, _ = context
    first = await reserve(sessions, ids)
    await reserve(sessions, ids, 60, ids.extended_type)
    async with sessions() as session:
        appointment = await session.get(Appointment, first)
        before = (
            appointment.start_time,
            appointment.end_time,
            appointment.end_with_buffer,
            appointment.status,
        )
    response = await client.patch(
        f"/api/v1/admin/appointment-types/{ids.type}",
        json={"duration_minutes": 40, "buffer_minutes": 0},
        headers=ids.headers(),
    )
    assert response.status_code == 200
    response = await client.patch(
        f"/api/v1/admin/doctors/{ids.doctor}",
        json={"max_appointments_per_window": 1},
        headers=ids.headers(),
    )
    assert response.status_code == 200
    assert await offered(client, ids) == []
    async with sessions() as session:
        appointment = await session.get(Appointment, first)
        assert (
            appointment.start_time,
            appointment.end_time,
            appointment.end_with_buffer,
            appointment.status,
        ) == before


async def test_changed_settings_ignore_old_cache_and_redis_failure_uses_database(context):
    ids, client, redis = context
    before = await offered(client, ids)
    response = await client.patch(
        f"/api/v1/admin/appointment-types/{ids.type}",
        json={"duration_minutes": 30, "buffer_minutes": 0},
        headers=ids.headers(),
    )
    assert response.status_code == 200
    after = await offered(client, ids)
    assert before[0]["end_time"] != after[0]["end_time"]
    assert len(next(iter(redis.values.values()))) == 2
    redis.fail = True
    assert await offered(client, ids) == after


@pytest.mark.parametrize("setting", ["capacity", "timing"])
async def test_failed_commit_preserves_configuration_and_audit(
    context, sessions, monkeypatch, setting
):
    ids, _, _ = context
    async with sessions() as session:
        before = await session.scalar(select(func.count(AuditLog.id)))
        admin = await session.get(User, ids.admin)
        monkeypatch.setattr(session, "commit", AsyncMock(side_effect=SQLAlchemyError("failed")))
        with pytest.raises(Conflict, match="Previous settings remain effective"):
            if setting == "capacity":
                await admin_api.update_doctor(
                    ids.doctor, DoctorUpdate(max_appointments_per_window=7), admin, session
                )
            else:
                await admin_api.update_appointment_type(
                    ids.type, AppointmentTypeUpdate(duration_minutes=40), admin, session
                )
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        assert doctor.max_appointments_per_window == 3
        appointment_type = await session.get(AppointmentType, ids.type)
        assert appointment_type.duration_minutes == 20
        assert await session.scalar(select(func.count(AuditLog.id))) == before


@pytest.mark.parametrize("setting", ["capacity", "timing"])
async def test_configuration_change_waits_for_inflight_reservation(
    context, sessions, monkeypatch, setting
):
    ids, _, _ = context
    locked, release = asyncio.Event(), asyncio.Event()
    original = availability.compute_slots

    async def pause_after_locks(*args, **kwargs):
        locked.set()
        await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(availability, "compute_slots", pause_after_locks)
    reservation = asyncio.create_task(reserve(sessions, ids))
    await asyncio.wait_for(locked.wait(), timeout=5)

    async def edit():
        async with sessions() as session:
            admin = await session.get(User, ids.admin)
            if setting == "capacity":
                return await admin_api.update_doctor(
                    ids.doctor, DoctorUpdate(max_appointments_per_window=1), admin, session
                )
            return await admin_api.update_appointment_type(
                ids.type, AppointmentTypeUpdate(duration_minutes=40), admin, session
            )

    change = asyncio.create_task(edit())
    try:
        # The edit must stay blocked until the old-rules reservation is committed.
        await asyncio.sleep(0.1)
        assert not change.done()
    finally:
        release.set()
    appointment_id, _ = await asyncio.wait_for(asyncio.gather(reservation, change), timeout=5)
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.end_time - appointment.start_time == timedelta(minutes=20)
        assert appointment.end_with_buffer - appointment.end_time == timedelta(minutes=10)


async def test_cancelled_and_rejected_bookings_release_window_capacity(context, sessions):
    ids, client, _ = context
    appointment_id = await reserve(sessions, ids)
    for status in (AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED):
        async with sessions() as session:
            appointment = await session.get(Appointment, appointment_id)
            appointment.status = status
            await session.commit()
        # Force a fresh computation, independent of browse TTL.
        async with sessions() as session:
            appointment_type = await session.get(AppointmentType, ids.type)
            slots = await availability.compute_slots(session, ids.doctor, appointment_type, ids.day)
            assert slots[0].start == ids.start


async def test_erp_schedule_replacement_takes_doctor_lock_and_versions_cache(context, sessions):
    ids, _, _ = context
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        doctor.erp_doctor_id = f"ERP-{uuid.uuid4().hex}"
        await session.commit()
        old_revision = doctor.updated_at
    async with sessions() as holder:
        await holder.execute(select(Doctor.id).where(Doctor.id == ids.doctor).with_for_update())

        async def sync():
            async with sessions() as session:
                return await erp_sync.sync_all_schedules(session, InMemoryErpAdapter())

        task = asyncio.create_task(sync())
        try:
            await asyncio.sleep(0.1)
            assert not task.done()
        finally:
            await holder.rollback()
        await asyncio.wait_for(task, timeout=5)
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        assert doctor.updated_at > old_revision


async def test_database_default_and_constraint(context, sessions):
    ids, client, _ = context
    async with sessions() as session:
        original = await session.get(Doctor, ids.doctor)
        department_id = original.department_id
    response = await client.post(
        "/api/v1/admin/doctors",
        json={"department_id": department_id, "full_name": "New doctor"},
        headers=ids.headers(),
    )
    assert response.status_code == 201
    assert response.json()["max_appointments_per_window"] == 1
    async with sessions() as session:
        doctor = await session.get(Doctor, response.json()["id"])
        doctor.max_appointments_per_window = 0
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        doctor = await session.get(Doctor, response.json()["id"])
        assert doctor.max_appointments_per_window == 1


async def test_missing_schedule_invalid_type_and_stricter_erp_limit(context, sessions):
    ids, client, _ = context
    async with sessions() as session:
        window = await session.scalar(
            select(DoctorSchedule).where(DoctorSchedule.doctor_id == ids.doctor)
        )
        window.max_appointments = 1
        await session.commit()
    await reserve(sessions, ids)
    assert await offered(client, ids) == []
    invalid = await client.get(
        f"/api/v1/doctors/{ids.doctor}/availability",
        params={"date": ids.day.isoformat(), "appointment_type_id": 2147483647},
    )
    assert invalid.status_code == 422
    async with sessions() as session:
        window = await session.scalar(
            select(DoctorSchedule).where(DoctorSchedule.doctor_id == ids.doctor)
        )
        await session.delete(window)
        await session.commit()
    async with sessions() as session:
        appointment_type = await session.get(AppointmentType, ids.type)
        assert (
            await availability.compute_slots(session, ids.doctor, appointment_type, ids.day) == []
        )


async def test_waiting_booking_refreshes_preloaded_type_after_admin_commit(context, sessions):
    ids, _, _ = context
    async with sessions() as holder, sessions() as waiting:
        # Deliberately leave the old timing in the booking session's identity map.
        stale_type = await waiting.get(AppointmentType, ids.type)
        assert stale_type.duration_minutes == 20
        patient = await waiting.get(PatientProfile, ids.patient)
        current = await holder.scalar(
            select(AppointmentType).where(AppointmentType.id == ids.type).with_for_update()
        )
        current.duration_minutes = 40
        await holder.flush()
        task = asyncio.create_task(
            booking.create_appointment(
                waiting,
                MemoryRedis(),
                InMemoryErpAdapter(),
                patient,
                AppointmentCreate.model_validate(ids.payload()),
                None,
            )
        )
        try:
            await asyncio.sleep(0.1)
            assert not task.done()
        finally:
            await holder.commit()
        appointment_id = await asyncio.wait_for(task, timeout=5)
    async with sessions() as session:
        appointment = await session.get(Appointment, appointment_id)
        assert appointment.end_time - appointment.start_time == timedelta(minutes=40)
