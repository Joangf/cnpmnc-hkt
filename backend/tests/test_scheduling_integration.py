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
        cwd=BACKEND_DIR, env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL}, check=True,
    )


@pytest.fixture
async def sessions(migrated):
    engine = create_async_engine(TEST_DATABASE_URL, pool_size=10)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def seed(session: AsyncSession) -> Seed:
    suffix = uuid.uuid4().hex
    patient = User(
        email=f"patient-{suffix}@example.com", password_hash="unused",
        role=UserRole.PATIENT, account_status=AccountStatus.ACTIVE,
    )
    patient.profile = PatientProfile(full_name="Test patient")
    admin = User(
        email=f"admin-{suffix}@example.com", password_hash="unused",
        role=UserRole.ADMIN, account_status=AccountStatus.ACTIVE,
    )
    specialty, other = Specialty(name=f"Primary-{suffix}"), Specialty(name=f"Other-{suffix}")
    hospital = Hospital(name="Test hospital", address="1 Test St", city="Test city")
    session.add_all([patient, admin, specialty, other, hospital])
    await session.flush()
    department = Department(name="Test department", hospital_id=hospital.id,
                            specialty_id=specialty.id)
    session.add(department)
    await session.flush()
    doctor = Doctor(
        full_name="Test doctor", hospital_id=hospital.id, department_id=department.id,
        max_appointments_per_window=3, scheduling_mode=SchedulingMode.ERP,
    )
    standard = AppointmentType(name="Standard", duration_minutes=20, buffer_minutes=10)
    extended = AppointmentType(name="Extended", duration_minutes=30, buffer_minutes=10)
    session.add_all([doctor, standard, extended])
    await session.flush()
    tomorrow = datetime.now(availability.clinic_tz()).date() + timedelta(days=1)
    start = datetime.combine(tomorrow, time(8), tzinfo=availability.clinic_tz()).astimezone(UTC)
    session.add(DoctorSchedule(
        doctor_id=doctor.id, start_time=start, end_time=start + timedelta(hours=3),
        max_appointments=None,
    ))
    await session.commit()
    return Seed(doctor.id, standard.id, extended.id, patient.profile.id, patient.id,
                admin.id, specialty.id, other.id, start)


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
    """Seed a historical window reservation for migration tests, without calling current APIs."""
    async with sessions() as session:
        start = ids.start + timedelta(minutes=offset)
        appointment = Appointment(
            booking_reference=uuid.uuid4().hex[:16], doctor_id=ids.doctor, patient_id=ids.patient,
            appointment_type_id=type_id or ids.type, start_time=start,
            end_time=start + timedelta(minutes=20), end_with_buffer=start + timedelta(minutes=30),
            status=AppointmentStatus.CONFIRMED, fee_amount=0, currency="VND",
        )
        session.add(appointment)
        await session.commit()
        return appointment.id


@pytest.mark.parametrize("role,expected", [(None, 401), ("PATIENT", 403)])
async def test_admin_settings_cannot_be_changed_by_guest_or_patient(context, role, expected):
    ids, client, _ = context
    for path, body in [
        (f"doctors/{ids.doctor}", {"max_appointments_per_window": 9}),
        (f"appointment-types/{ids.type}", {"duration_minutes": 40}),
    ]:
        response = await client.patch(f"/api/v1/admin/{path}", json=body,
                                      headers=ids.headers(role) if role else {})
        assert response.status_code == expected


