"""Doctor reviews (FRD 4.8): eligibility (BR-08), one per appointment (BR-09), moderation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, InvalidState, NotFound, ValidationFailed
from app.models import PatientProfile, Review, ReviewReport, User
from app.models.base import utcnow
from app.models.enums import AppointmentStatus, CheckInStatus, ReviewStatus
from app.repositories import appointments as appointment_repo
from app.repositories import reviews as review_repo
from app.schemas.reviews import ReportCreate, ReviewCreate, ReviewUpdate
from app.services import audit


async def create_review(
    session: AsyncSession, patient: PatientProfile, appointment_id: int, payload: ReviewCreate
) -> Review:
    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound("Appointment not found.")
    if appointment.status != AppointmentStatus.COMPLETED:
        raise InvalidState(
            "Reviews can only be submitted after a completed appointment.", code="ReviewNotEligible"
        )
    if appointment.check_in_status != CheckInStatus.CHECKED_IN:
        # SCRUM-44: the hospital must have confirmed the visit (ERP check-in), not just completion.
        raise InvalidState(
            "Reviews need a visit the hospital confirmed you checked in to.",
            code="ReviewNotEligible",
        )
    if appointment.review is not None:
        raise Conflict("You have already reviewed this appointment.", code="DuplicateReview")

    review = Review(
        appointment_id=appointment.id,
        patient_id=patient.id,
        doctor_id=appointment.doctor_id,
        rating=payload.rating,
        comment=payload.comment or None,
        status=ReviewStatus.PENDING
        if settings.review_requires_approval
        else ReviewStatus.PUBLISHED,
    )
    session.add(review)
    try:
        await session.flush()
    except IntegrityError as exc:  # unique(appointment_id) under a race
        await session.rollback()
        raise Conflict(
            "You have already reviewed this appointment.", code="DuplicateReview"
        ) from exc

    await review_repo.recompute_doctor_rating(session, review.doctor_id)
    audit.record(
        session,
        "review.created",
        "review",
        review.id,
        actor_id=patient.user_id,
        details={"doctor_id": review.doctor_id, "rating": review.rating},
    )
    await session.commit()
    return review


async def moderate(
    session: AsyncSession, admin: User, review_id: int, status: ReviewStatus, note: str | None
) -> Review:
    review = await review_repo.get(session, review_id)
    if review is None:
        raise NotFound("Review not found.")
    old_status = review.status
    review.status = status
    review.moderated_by = admin.id
    review.moderation_note = note
    await session.flush()
    await review_repo.recompute_doctor_rating(session, review.doctor_id)
    # The decision closes the queue for this review: PUBLISHED = reports dismissed.
    resolved = await session.execute(
        update(ReviewReport)
        .where(ReviewReport.review_id == review.id, ReviewReport.status == "OPEN")
        .values(status="RESOLVED", resolution=status, resolved_by=admin.id, resolved_at=utcnow())
    )
    audit.record(
        session,
        "review.moderated",
        "review",
        review.id,
        actor_id=admin.id,
        details={"from": old_status, "to": status, "reports_resolved": resolved.rowcount},
    )
    await session.commit()
    return review


async def delete_review(session: AsyncSession, admin: User, review_id: int) -> None:
    review = await review_repo.get(session, review_id)
    if review is None:
        raise NotFound("Review not found.")
    doctor_id = review.doctor_id
    # Reports of a deleted review have nothing left to decide (and would block the delete).
    await session.execute(delete(ReviewReport).where(ReviewReport.review_id == review_id))
    await session.delete(review)
    await session.flush()
    await review_repo.recompute_doctor_rating(session, doctor_id)
    audit.record(
        session,
        "review.deleted",
        "review",
        review_id,
        actor_id=admin.id,
        details={"doctor_id": doctor_id},
    )
    await session.commit()


async def update_review(
    session: AsyncSession, patient: PatientProfile, appointment_id: int, payload: ReviewUpdate
) -> Review:
    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound("Appointment not found.")
    review = appointment.review
    if review is None:
        raise NotFound("Review not found for this appointment.")

    # Ràng buộc 1: Giới hạn số lần sửa tối đa 1 lần
    if getattr(review, "is_edited", False):
        raise InvalidState("Review can only be edited once.", code="AlreadyEdited")

    # Ràng buộc 2: Giới hạn thời gian trong vòng 24 giờ
    now = datetime.now(UTC)
    created_at = review.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if (now - created_at) > timedelta(hours=24):
        raise InvalidState(
            "Reviews can only be edited within 24 hours of creation.", code="EditWindowExpired"
        )

    review.rating = payload.rating
    review.comment = payload.comment or None
    review.is_edited = True
    if settings.review_requires_approval:
        review.status = ReviewStatus.PENDING

    await session.flush()
    await review_repo.recompute_doctor_rating(session, review.doctor_id)
    audit.record(
        session,
        "review.updated",
        "review",
        review.id,
        actor_id=patient.user_id,
        details={"doctor_id": review.doctor_id, "rating": review.rating},
    )
    await session.commit()
    return review


async def report_review(
    session: AsyncSession, reporter: PatientProfile, review_id: int, payload: ReportCreate
) -> tuple[ReviewReport, bool]:
    """SCRUM-50. Returns (report, created). A second report of the same review by the same
    patient while one is open returns the open one instead of piling up duplicates."""
    review = await review_repo.get(session, review_id)
    if review is None or review.status != ReviewStatus.PUBLISHED:
        # Hidden/removed/unknown look the same: nothing about them is revealed.
        raise NotFound("Review not found.")
    if payload.reason not in settings.review_report_reasons:
        raise ValidationFailed("Choose one of the listed reasons.")
    existing = await session.scalar(
        select(ReviewReport).where(
            ReviewReport.review_id == review_id,
            ReviewReport.reporter_user_id == reporter.user_id,
            ReviewReport.status == "OPEN",
        )
    )
    if existing is not None:
        return existing, False
    report = ReviewReport(
        review_id=review_id,
        reporter_user_id=reporter.user_id,
        reason=payload.reason,
        details=payload.details or None,
        status="OPEN",
    )
    session.add(report)
    try:
        await session.flush()
    except IntegrityError:  # a concurrent duplicate: return the one that won
        await session.rollback()
        existing = await session.scalar(
            select(ReviewReport).where(
                ReviewReport.review_id == review_id,
                ReviewReport.reporter_user_id == reporter.user_id,
                ReviewReport.status == "OPEN",
            )
        )
        if existing is None:
            raise
        return existing, False
    audit.record(
        session,
        "review.reported",
        "review",
        review_id,
        actor_id=reporter.user_id,
        details={"report_id": report.id, "reason": payload.reason},
    )
    await session.commit()
    return report, True
