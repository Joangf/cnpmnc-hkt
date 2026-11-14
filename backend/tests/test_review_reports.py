"""Sprint 6 reviews: reporting (SCRUM-50), moderation of reports (SCRUM-47) and rating
aggregates (SCRUM-49), against TEST_DATABASE_URL. Rows use uuid suffixes."""

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.errors import NotFound, ValidationFailed
from app.models import (
    Appointment,
    AppointmentType,
    Department,
    Doctor,
    Hospital,
    PatientProfile,
    Review,
    ReviewReport,
    Specialty,
    User,
)
from app.models.enums import AccountStatus, AppointmentStatus, ReviewStatus, UserRole
from app.repositories import reviews as review_repo
from app.schemas.reviews import ReportCreate
from app.services import reviews as review_service

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")
BACKEND_DIR = Path(__file__).resolve().parents[1]
REASON = settings.review_report_reasons[0]


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
    engine = create_async_engine(TEST_DATABASE_URL, pool_size=5)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _patient(session, tag: str, name: str) -> PatientProfile:
    user = User(
        email=f"rev-{name}-{tag}@example.com",
        password_hash="unused",
        role=UserRole.PATIENT,
        account_status=AccountStatus.ACTIVE,
    )
    user.profile = PatientProfile(full_name=f"Rev {name}")
    session.add(user)
    await session.flush()
    return user.profile


@pytest.fixture
async def world(sessions):
    """A doctor with two published reviews (5 and 3 stars) by one patient; a second patient."""
    tag = uuid.uuid4().hex
    async with sessions() as session:
        author = await _patient(session, tag, "author")
        reporter = await _patient(session, tag, "reporter")
        admin = User(
            email=f"rev-admin-{tag}@example.com",
            password_hash="unused",
            role=UserRole.ADMIN,
            account_status=AccountStatus.ACTIVE,
        )
        specialty = Specialty(name=f"Rev-{tag}")
        hospital = Hospital(name="Rev hospital", address="1 Rev St", city="Rev city")
        session.add_all([admin, specialty, hospital])
        await session.flush()
        department = Department(name="Rev dept", hospital_id=hospital.id, specialty_id=specialty.id)
        session.add(department)
        await session.flush()
        doctor = Doctor(
            full_name=f"Rev doctor {tag}", hospital_id=hospital.id, department_id=department.id
        )
        appointment_type = AppointmentType(
            name=f"Rev type {tag}", duration_minutes=20, fee_override=Decimal("1000")
        )
        session.add_all([doctor, appointment_type])
        await session.flush()
        reviews = []
        for i, rating in enumerate((5, 3)):
            start = datetime.now(UTC) - timedelta(days=10 + i)
            appointment = Appointment(
                booking_reference=f"R{tag[:10]}{i}",
                patient_id=author.id,
                doctor_id=doctor.id,
                appointment_type_id=appointment_type.id,
                start_time=start,
                end_time=start + timedelta(minutes=20),
                end_with_buffer=start + timedelta(minutes=20),
                status=AppointmentStatus.COMPLETED,
                fee_amount=Decimal("1000"),
                currency="VND",
            )
            session.add(appointment)
            await session.flush()
            review = Review(
                appointment_id=appointment.id,
                patient_id=author.id,
                doctor_id=doctor.id,
                rating=rating,
                comment=f"comment {i}",
                status=ReviewStatus.PUBLISHED,
            )
            session.add(review)
            await session.flush()
            reviews.append(review.id)
        await session.commit()
        return {"reporter": reporter, "admin": admin, "doctor": doctor.id, "reviews": reviews}


async def test_report_is_idempotent_and_does_not_hide_the_review(sessions, world) -> None:
    review_id = world["reviews"][0]
    async with sessions() as session:
        first, created = await review_service.report_review(
            session, world["reporter"], review_id, ReportCreate(reason=REASON, details="rude")
        )
        again, created_again = await review_service.report_review(
            session, world["reporter"], review_id, ReportCreate(reason=REASON)
        )
        review = await session.get(Review, review_id)
    assert created and not created_again and again.id == first.id
    assert review.status == ReviewStatus.PUBLISHED  # reporting decides nothing


async def test_unknown_reason_and_hidden_review_are_rejected(sessions, world) -> None:
    review_id = world["reviews"][0]
    async with sessions() as session:
        with pytest.raises(ValidationFailed):
            await review_service.report_review(
                session, world["reporter"], review_id, ReportCreate(reason="made up")
            )
        await review_service.moderate(session, world["admin"], review_id, ReviewStatus.HIDDEN, None)
        with pytest.raises(NotFound):
            await review_service.report_review(
                session, world["reporter"], review_id, ReportCreate(reason=REASON)
            )


async def test_moderation_resolves_open_reports_and_updates_the_rating(sessions, world) -> None:
    review_id = world["reviews"][1]  # the 3-star review
    async with sessions() as session:
        await review_service.report_review(
            session, world["reporter"], review_id, ReportCreate(reason=REASON)
        )
        queue, _ = await review_repo.list_admin(
            session, status=None, doctor_id=world["doctor"], page=1, page_size=10, reported=True
        )
        assert [r.id for r in queue] == [review_id]

        await review_service.moderate(session, world["admin"], review_id, ReviewStatus.REMOVED, "x")
        reports = (
            await session.scalars(select(ReviewReport).where(ReviewReport.review_id == review_id))
        ).all()
        doctor = await session.get(Doctor, world["doctor"], populate_existing=True)
    assert [(r.status, r.resolution) for r in reports] == [("RESOLVED", "REMOVED")]
    assert (doctor.rating_avg, doctor.rating_count) == (Decimal("5.00"), 1)


async def test_reconciliation_rebuilds_a_drifted_aggregate(sessions, world) -> None:
    async with sessions() as session:
        doctor = await session.get(Doctor, world["doctor"])
        doctor.rating_avg, doctor.rating_count = Decimal("1.00"), 99  # drifted
        await session.commit()
        await review_repo.recompute_all_ratings(session)
        await session.commit()
        doctor = await session.get(Doctor, world["doctor"], populate_existing=True)
    assert (doctor.rating_avg, doctor.rating_count) == (Decimal("4.00"), 2)


async def test_review_needs_confirmed_check_in_and_completion(sessions, world) -> None:
    """SCRUM-44: completed but never checked in, or checked in but unfinished -> rejected."""
    from app.core.errors import InvalidState
    from app.models.enums import CheckInStatus
    from app.schemas.reviews import ReviewCreate
    from app.services import policies

    async with sessions() as session:
        patient = world["reporter"]
        doctor = await session.get(Doctor, world["doctor"])
        appointment_type = await session.scalar(
            select(AppointmentType).order_by(AppointmentType.id.desc())
        )
        cases = {
            "completed_no_check_in": (AppointmentStatus.COMPLETED, CheckInStatus.NOT_CHECKED_IN),
            "checked_in_unfinished": (AppointmentStatus.CONFIRMED, CheckInStatus.CHECKED_IN),
            "eligible": (AppointmentStatus.COMPLETED, CheckInStatus.CHECKED_IN),
        }
        ids = {}
        for i, (name, (status, check_in)) in enumerate(cases.items()):
            start = datetime.now(UTC) - timedelta(days=3 + i)
            appointment = Appointment(
                booking_reference=f"C{uuid.uuid4().hex[:10]}",
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_type_id=appointment_type.id,
                start_time=start,
                end_time=start + timedelta(minutes=20),
                end_with_buffer=start + timedelta(minutes=20),
                status=status,
                check_in_status=check_in,
                fee_amount=Decimal("1000"),
                currency="VND",
            )
            session.add(appointment)
            await session.flush()
            ids[name] = appointment.id
        await session.commit()

        for name in ("completed_no_check_in", "checked_in_unfinished"):
            with pytest.raises(InvalidState):
                await review_service.create_review(
                    session, patient, ids[name], ReviewCreate(rating=4)
                )
        review = await review_service.create_review(
            session, patient, ids["eligible"], ReviewCreate(rating=4, comment="ok")
        )
        appointment = await session.get(Appointment, ids["eligible"], populate_existing=True)
        await session.refresh(appointment, ["review"])
    assert review.rating == 4
    assert not policies.can_review(appointment)  # one review per appointment
