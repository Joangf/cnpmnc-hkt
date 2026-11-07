"""Integration tests: booking capacity and overlap rules are enforced atomically on the server
(SCRUM-24, FR-BOOK-04/05, BR-03/04).

Drives `booking.create_appointment` against a real PostgreSQL, so the per-doctor capacity lock,
the `no_overlap` exclusion constraint and the transaction boundaries are all exercised.

Requires TEST_DATABASE_URL (set in docker-compose.override.yml).
"""

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import SlotTaken
from app.models import (
    Appointment,
    AppointmentType,
    Department,
    Doctor,
    DoctorSchedule,
    Hospital,
    PatientProfile,
    Specialty,
    User,
)
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus, SchedulingMode
from app.schemas.appointments import AppointmentCreate
from app.services import availability, booking

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

BACKEND_DIR = Path(__file__).resolve().parents[1]


class _NullRedis:
    """Availability-cache invalidation target; the cache is irrelevant to these tests."""

    async def delete(self, *keys: str) -> int:
        return 0


@pytest.fixture(scope="module")
def database_url() -> str:
    assert TEST_DATABASE_URL
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    for args in (["downgrade", "base"], ["upgrade", "head"]):
        subprocess.run(
            [sys.executable, "-m", "alembic", *args], check=True, env=env, cwd=BACKEND_DIR
        )
    return TEST_DATABASE_URL


@pytest.fixture
async def sessions(database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, pool_size=25, max_overflow=0)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _clinic_day() -> date:
    """A day inside the booking horizon and far enough ahead for the minimum lead time."""
    return availability.local_day(datetime.now(UTC)) + timedelta(days=2)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(_clinic_day(), time(hour, minute), tzinfo=availability.clinic_tz())


class World:
    """One isolated doctor (plus a second doctor in the same department) and a patient."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions
        self.patient_id = 0
        self.doctor_id = 0
        self.other_doctor_id = 0
        self.types: dict[str, int] = {}

    async def build(
        self,
        windows: list[tuple[datetime, datetime, int | None]],
        *,
        other_doctor: bool = False,
        doctor_capacity: int = 100,
    ) -> "World":
        tag = uuid.uuid4().hex[:8]
        async with self.sessions() as s:
            user = User(email=f"cap-{tag}@example.com", password_hash="x")
            user.profile = PatientProfile(full_name="Capacity Test")
            specialty = Specialty(name=f"Spec {tag}")
            hospital = Hospital(name=f"Hospital {tag}", address="1 Test St", city="Test City")
            s.add_all([user, specialty, hospital])
            await s.flush()
            department = Department(hospital_id=hospital.id, specialty_id=specialty.id, name="D")
            s.add(department)
            await s.flush()
            doctors = [
                Doctor(
                    hospital_id=hospital.id,
                    department_id=department.id,
                    full_name=f"Dr {i}",
                    # Doctor-level capacity (SCRUM-21). High by default so each test's window
                    # `max_appointments` is the binding limit unless the test says otherwise.
                    max_appointments_per_window=doctor_capacity,
                    scheduling_mode=SchedulingMode.ERP,  # Exercise legacy ERP window rules.
                )
                for i in range(2 if other_doctor else 1)
            ]
            # Scoped to this doctor so concurrent tests never see each other's types.
            s.add_all(doctors)
            await s.flush()
            short = AppointmentType(
                name="Short", duration_minutes=20, buffer_minutes=10, doctor_id=doctors[0].id
            )
            long = AppointmentType(
                name="Long", duration_minutes=60, buffer_minutes=0, doctor_id=doctors[0].id
            )
            s.add_all([short, long])
            if other_doctor:
                s.add(
                    AppointmentType(
                        name="Short",
                        duration_minutes=20,
                        buffer_minutes=10,
                        doctor_id=doctors[1].id,
                    )
                )
            for doctor in doctors:
                s.add_all(
                    DoctorSchedule(
                        doctor_id=doctor.id, start_time=a, end_time=b, max_appointments=m
                    )
                    for a, b, m in windows
                )
            await s.commit()
            assert user.profile is not None
            self.patient_id = user.profile.id
            self.doctor_id = doctors[0].id
            self.other_doctor_id = doctors[1].id if other_doctor else 0
            self.types = {"short": short.id, "long": long.id}
        return self

    async def book(self, start: datetime, kind: str = "short", doctor_id: int | None = None) -> int:
        doctor_id = doctor_id or self.doctor_id
        async with self.sessions() as s:
            if doctor_id == self.other_doctor_id:
                type_id = await s.scalar(
                    select(AppointmentType.id).where(AppointmentType.doctor_id == doctor_id)
                )
            else:
                type_id = self.types[kind]
            patient = await s.get(PatientProfile, self.patient_id)
            assert patient is not None and type_id is not None
            payload = AppointmentCreate(
                doctor_id=doctor_id, appointment_type_id=type_id, start_time=start
            )
            return await booking.create_appointment(
                s,
                _NullRedis(),
                None,
                patient,
                payload,
                None,  # type: ignore[arg-type]
            )

    async def try_book(self, start: datetime, kind: str = "short", doctor_id: int | None = None):
        """Returns the appointment id, or the SlotTaken error that rejected the request."""
        try:
            return await self.book(start, kind, doctor_id)
        except SlotTaken as exc:
            return exc

    async def active_count(self, doctor_id: int | None = None) -> int:
        async with self.sessions() as s:
            return (
                await s.scalar(
                    select(func.count(Appointment.id)).where(
                        Appointment.doctor_id == (doctor_id or self.doctor_id),
                        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                    )
                )
                or 0
            )


def _rejected(result: object) -> bool:
    return isinstance(result, SlotTaken) and result.status_code == 409


# --- AC-3: concurrency -------------------------------------------------------------------------


async def test_concurrent_requests_cannot_exceed_window_capacity(sessions) -> None:
    """8 simultaneous requests for 8 different, non-overlapping times in a window that only has
    2 places left: exactly 2 succeed. Overlap rules alone cannot catch this; capacity must be
    checked and reserved atomically."""
    world = await World(sessions).build([(at(9), at(13), 2)])
    starts = [at(9) + timedelta(minutes=30 * i) for i in range(8)]

    results = await asyncio.gather(*(world.try_book(s) for s in starts))

    assert sum(isinstance(r, int) for r in results) == 2
    assert all(_rejected(r) for r in results if not isinstance(r, int))
    assert await world.active_count() == 2


async def test_concurrent_requests_respect_doctor_level_capacity(sessions) -> None:
    """Same race, but the binding limit is the doctor's configured capacity (SCRUM-21)."""
    world = await World(sessions).build([(at(9), at(13), None)], doctor_capacity=3)
    starts = [at(9) + timedelta(minutes=30 * i) for i in range(8)]

    results = await asyncio.gather(*(world.try_book(s) for s in starts))

    assert sum(isinstance(r, int) for r in results) == 3
    assert await world.active_count() == 3


async def test_concurrent_requests_for_the_same_slot_allow_exactly_one(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), None)])

    results = await asyncio.gather(*(world.try_book(at(10)) for _ in range(10)))

    assert sum(isinstance(r, int) for r in results) == 1
    assert all(_rejected(r) for r in results if not isinstance(r, int))
    assert await world.active_count() == 1


async def test_concurrent_staggered_overlaps_allow_exactly_one(sessions) -> None:
    """Partially overlapping requests (10 minutes apart, each reserving 30) racing each other."""
    world = await World(sessions).build([(at(9), at(12), None)])
    starts = [at(10) + timedelta(minutes=10 * (i % 3)) for i in range(9)]

    results = await asyncio.gather(*(world.try_book(s) for s in starts))

    assert sum(isinstance(r, int) for r in results) == 1
    assert await world.active_count() == 1


# --- AC-2 / AC-5: capacity --------------------------------------------------------------------


async def test_bookings_within_capacity_succeed_until_exhausted(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), 3)])

    for start in (at(9), at(9, 30), at(10)):
        assert isinstance(await world.try_book(start), int)
    rejected = await world.try_book(at(11))

    assert _rejected(rejected) and rejected.code == "SlotUnavailable"
    assert await world.active_count() == 3


async def test_cancelled_booking_frees_capacity(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), 1)])
    first = await world.book(at(9))
    assert _rejected(await world.try_book(at(10)))

    async with sessions() as s:
        appointment = await s.get(Appointment, first)
        assert appointment is not None
        appointment.status = AppointmentStatus.CANCELLED
        await s.commit()

    assert isinstance(await world.try_book(at(10)), int)


async def test_unlimited_window_accepts_every_non_overlapping_booking(sessions) -> None:
    world = await World(sessions).build([(at(9), at(11), None)])
    results = await asyncio.gather(
        *(world.try_book(at(9) + timedelta(minutes=30 * i)) for i in range(4))
    )
    assert all(isinstance(r, int) for r in results)


# --- AC-2 / AC-6: shared resource and interval boundaries -------------------------------------


async def test_doctor_is_a_shared_resource_across_appointment_types(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), None)], other_doctor=True)
    await world.book(at(9))  # short: reserves [09:00, 09:30)

    overlapping_long = await world.try_book(at(9, 10), kind="long")
    adjacent_long = await world.try_book(at(9, 30), kind="long")  # starts at buffer end
    other_doctor_same_time = await world.try_book(at(9), doctor_id=world.other_doctor_id)

    assert _rejected(overlapping_long)
    assert isinstance(adjacent_long, int)
    assert isinstance(other_doctor_same_time, int)


@pytest.mark.parametrize(
    ("minute", "accepted", "case"),
    [
        (30, True, "exactly adjacent after the existing booking's buffer"),
        (0, False, "identical start time"),
        (20, False, "starts inside the existing booking's buffer"),
        (-20, False, "own buffer overlaps the existing booking"),
        (-30, True, "own buffer ends exactly where the existing booking starts"),
    ],
)
async def test_interval_boundaries_against_a_stored_booking(
    sessions, minute: int, accepted: bool, case: str
) -> None:
    world = await World(sessions).build([(at(9), at(12), None)])
    await world.book(at(10))  # reserves [10:00, 10:30)

    result = await world.try_book(at(10) + timedelta(minutes=minute))

    assert isinstance(result, int) is accepted, case
    assert await world.active_count() == (2 if accepted else 1)


# --- AC-1 / AC-7: server-side revalidation of stale or crafted requests ------------------------


@pytest.mark.parametrize(
    ("start", "kind", "case"),
    [
        (lambda: at(9, 5), "short", "not on the slot grid"),
        (lambda: at(14), "short", "outside every schedule window"),
        (lambda: at(11, 30), "long", "duration runs past the window end"),
        (lambda: at(11, 40), "short", "buffer runs past the window end"),
    ],
)
async def test_requests_outside_the_permitted_schedule_are_rejected(
    sessions, start, kind: str, case: str
) -> None:
    world = await World(sessions).build([(at(9), at(12), None)])

    result = await world.try_book(start(), kind=kind)

    assert _rejected(result) and result.code == "SlotUnavailable", case
    assert await world.active_count() == 0


async def test_unavailable_schedule_block_is_respected(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), None)])
    async with sessions() as s:
        s.add(
            DoctorSchedule(
                doctor_id=world.doctor_id, start_time=at(10), end_time=at(11), is_available=False
            )
        )
        await s.commit()

    assert _rejected(await world.try_book(at(10, 30)))
    assert isinstance(await world.try_book(at(11)), int)


# --- AC-4 / AC-8: persistence failure during reservation --------------------------------------


async def test_failure_after_reserving_rolls_everything_back(sessions, monkeypatch) -> None:
    """A write failure after the appointment row is flushed (but before commit) must leave no
    booking and no consumed capacity behind."""
    world = await World(sessions).build([(at(9), at(12), 1)])

    async def broken_notify(*args, **kwargs):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(booking.notifications, "notify_patient", broken_notify)
    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        await world.book(at(10))
    monkeypatch.undo()

    assert await world.active_count() == 0
    async with sessions() as s:
        total = await s.scalar(
            select(func.count(Appointment.id)).where(Appointment.doctor_id == world.doctor_id)
        )
    assert total == 0
    # The single place is still available.
    assert isinstance(await world.try_book(at(10)), int)


async def test_rejected_conflict_returns_identifiable_result_and_leaves_nothing(sessions) -> None:
    world = await World(sessions).build([(at(9), at(12), None)])
    await world.book(at(10))

    result = await world.try_book(at(10))

    assert isinstance(result, SlotTaken)
    assert result.status_code == 409 and result.code in {"SlotTaken", "SlotUnavailable"}
    async with sessions() as s:
        total = await s.scalar(
            select(func.count(Appointment.id)).where(Appointment.doctor_id == world.doctor_id)
        )
    assert total == 1
