"""Doctor reviews (FRD 4.8): eligibility (BR-08), one per appointment (BR-09), moderation."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, InvalidState, NotFound
from app.models import PatientProfile, Review, User
from app.models.enums import AppointmentStatus, ReviewStatus
from app.repositories import appointments as appointment_repo
from app.repositories import reviews as review_repo
from app.schemas.reviews import ReviewCreate
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
    audit.record(
        session,
        "review.moderated",
        "review",
        review.id,
        actor_id=admin.id,
        details={"from": old_status, "to": status},
    )
    await session.commit()
    return review
