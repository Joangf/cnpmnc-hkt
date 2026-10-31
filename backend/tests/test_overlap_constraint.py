"""Integration test: the `no_overlap` exclusion constraint prevents double booking under
concurrency (FR-BOOK-05, NFR-06).

Requires TEST_DATABASE_URL (set in docker-compose.override.yml)."""

import asyncio
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Appointment,
    AppointmentType,
    Department,
    Doctor,
    Hospital,
    PatientProfile,
    Specialty,
    User,
)
from app.models.enums import AppointmentStatus

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

BACKEND_DIR = Path(__file__).resolve().parents[1]
START = datetime(2030, 1, 7, 2, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def database_url() -> str:
    assert TEST_DATABASE_URL
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *args], check=True, env=env, cwd=BACKEND_DIR
        )
    return TEST_DATABASE_URL


async def _seed(session: AsyncSession) -> tuple[int, int, int]:
    user = User(email="race@example.com", password_hash="x")
    user.profile = PatientProfile(
        full_name="Race Test", date_of_birth=date(1990, 1, 1), phone_number="+84900000000"
    )
    specialty = Specialty(name="Test Specialty")
    hospital = Hospital(name="Test Hospital", address="1 Test St", city="Test City")
    session.add_all([user, specialty, hospital])
    await session.flush()
    department = Department(hospital_id=hospital.id, specialty_id=specialty.id, name="Test Dept")
    session.add(department)
    await session.flush()
    doctor = Doctor(hospital_id=hospital.id, department_id=department.id, full_name="Dr. Test")
    appointment_type = AppointmentType(name="Std", duration_minutes=20, buffer_minutes=10)
    session.add_all([doctor, appointment_type])
    await session.commit()
    assert user.profile is not None
    return user.profile.id, doctor.id, appointment_type.id


def _appointment(
    ref: str, ids: tuple[int, int, int], start: datetime, status: AppointmentStatus
) -> Appointment:
    patient_id, doctor_id, type_id = ids
    return Appointment(
        booking_reference=ref,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_type_id=type_id,
        start_time=start,
        end_time=start + timedelta(minutes=20),
        end_with_buffer=start + timedelta(minutes=30),
        status=status,
        fee_amount=Decimal("0"),
        currency="VND",
    )


async def test_concurrent_overlapping_bookings_allow_exactly_one(database_url: str) -> None:
    engine = create_async_engine(database_url, pool_size=20)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        ids = await _seed(session)

    async def attempt(i: int) -> bool:
        async with sessions() as session:
            # Staggered by 5 minutes: every candidate overlaps the 30-minute reserved range.
            session.add(
                _appointment(
                    f"RACE{i:04d}",
                    ids,
                    START + timedelta(minutes=5 * (i % 3)),
                    AppointmentStatus.PENDING,
                )
            )
            try:
                await session.commit()
                return True
            except IntegrityError:
                return False

    results = await asyncio.gather(*(attempt(i) for i in range(15)))
    assert results.count(True) == 1

    # Cancelled/rejected bookings do not hold the slot; back-to-back bookings are allowed.
    async with sessions() as session:
        session.add(
            _appointment("CANC0001", ids, START + timedelta(hours=2), AppointmentStatus.CANCELLED)
        )
        session.add(
            _appointment("NEXT0001", ids, START + timedelta(hours=2), AppointmentStatus.CONFIRMED)
        )
        session.add(
            _appointment(
                "NEXT0002", ids, START + timedelta(hours=2, minutes=30), AppointmentStatus.CONFIRMED
            )
        )
        await session.commit()

    await engine.dispose()
