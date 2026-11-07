"""Booking workflow (FRD 4.4, 5.1).

Order of operations:
1. Revalidate availability inside the request (BR-03).
2. Insert the appointment as PENDING; the `no_overlap` exclusion constraint rejects
   concurrent overlapping inserts atomically (FR-BOOK-05, BR-04).
3. Commit, then submit to the ERP. Only an ERP acceptance flips it to CONFIRMED (BR-02).
"""

from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErpUnavailable, InvalidState, NotFound, SlotTaken, ValidationFailed
from app.core.metrics import BOOKINGS
from app.core.security import generate_booking_reference
from app.integrations.erp.base import (
    ErpAdapter,
    ErpBookingRequest,
    ErpBookingResult,
    ErpRejectedError,
    ErpTimeoutError,
    ErpUnavailableError,
)
from app.integrations.payment.base import PaymentGateway
from app.models import Appointment, AppointmentType, Doctor, PatientProfile
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    AppointmentStatus,
    CheckInStatus,
    NotificationType,
    StatusSource,
)
from app.repositories import appointments as appointment_repo
from app.repositories import directory as directory_repo
from app.schemas.appointments import AppointmentCreate
from app.services import audit, availability, idempotency, notifications, policies
from app.services.scheduling_settings import resolve

logger = structlog.get_logger(__name__)

ALLOWED_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.REJECTED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.CANCELLED,
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
    },
}

_STATUS_MESSAGES: dict[AppointmentStatus, tuple[str, str]] = {
    AppointmentStatus.CONFIRMED: (
        "Appointment confirmed",
        "Your appointment {ref} on {when} has been confirmed by the hospital.",
    ),
    AppointmentStatus.REJECTED: (
        "Booking not accepted",
        "Your booking request {ref} for {when} was not accepted.",
    ),
    AppointmentStatus.CANCELLED: (
        "Appointment cancelled",
        "Your appointment {ref} on {when} has been cancelled.",
    ),
    AppointmentStatus.COMPLETED: (
        "Appointment completed",
        "Your appointment {ref} has been completed. You can now review your doctor.",
    ),
    AppointmentStatus.NO_SHOW: (
        "Missed appointment",
        "The hospital recorded appointment {ref} on {when} as missed.",
    ),
}


def can_transition(current: AppointmentStatus, new: AppointmentStatus) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, set())


def parse_status(value: str | None) -> AppointmentStatus | None:
    try:
        return AppointmentStatus(value) if value else None
    except ValueError:
        return None


async def transition(
    session: AsyncSession,
    appointment: Appointment,
    new_status: AppointmentStatus,
    *,
    reason: str | None,
    source: StatusSource,
    actor_id: int | None = None,
) -> bool:
    """Apply a status change with history, audit and patient notification. Caller commits."""
    if appointment.status == new_status:
        return False
    if not can_transition(appointment.status, new_status):
        logger.warning(
            "appointment_transition_ignored",
            appointment_id=appointment.id,
            current=appointment.status,
            requested=new_status,
            source=source,
        )
        return False

    old_status = appointment.status
    appointment.status = new_status
    appointment.status_reason = reason[:500] if reason else None
    if new_status == AppointmentStatus.CANCELLED:
        appointment.cancelled_at = datetime.now(UTC)

    appointment_repo.add_history(
        session, appointment.id, "status", old_status, new_status, reason, source
    )
    audit.record(
        session,
        "appointment.status_changed",
        "appointment",
        appointment.id,
        actor_id=actor_id,
        actor_type=audit.actor_type_for(source),
        details={"from": old_status, "to": new_status, "source": source},
    )
    title, template = _STATUS_MESSAGES[new_status]
    content = template.format(
        ref=appointment.booking_reference, when=availability.format_local(appointment.start_time)
    )
    if reason:
        content += f" Reason: {reason}"
    await notifications.notify_patient(
        session,
        appointment.patient_id,
        NotificationType.APPOINTMENT_STATUS,
        title,
        content,
        f"/appointments/{appointment.id}",
    )
    return True


async def apply_erp_result(
    session: AsyncSession, appointment: Appointment, result: ErpBookingResult
) -> bool:
    if result.erp_booking_id and appointment.erp_booking_id != result.erp_booking_id:
        appointment.erp_booking_id = result.erp_booking_id
    new_status = parse_status(result.status)
    if new_status is None:
        logger.warning("erp_unknown_status", appointment_id=appointment.id, status=result.status)
        return False
    return await transition(
        session, appointment, new_status, reason=result.reason, source=StatusSource.ERP
    )


def _is_overlap_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None) or getattr(
        getattr(orig, "__cause__", None), "sqlstate", None
    )
    return sqlstate == "23P01" or "no_overlap" in str(exc)


async def create_appointment(
    session: AsyncSession,
    redis: Redis,
    erp: ErpAdapter,
    patient: PatientProfile,
    payload: AppointmentCreate,
    idempotency_key: str | None,
) -> int:
    """Create a booking and return its id. Safe to retry with the same Idempotency-Key."""
    user_id = patient.user_id
    if idempotency_key:
        existing = await idempotency.begin(redis, "booking", user_id, idempotency_key)
        if existing:
            return int(existing)
    try:
        appointment_id = await _create(session, redis, erp, patient.id, user_id, payload)
    except Exception:
        if idempotency_key:
            await idempotency.release(redis, "booking", user_id, idempotency_key)
        raise
    if idempotency_key:
        await idempotency.complete(redis, "booking", user_id, idempotency_key, appointment_id)
    return appointment_id


async def _create(
    session: AsyncSession,
    redis: Redis,
    erp: ErpAdapter,
    patient_id: int,
    user_id: int,
    payload: AppointmentCreate,
) -> int:
    # Consistent lock order: type (shared), then doctor (exclusive). Re-read after locking:
    # authentication / previous queries may have populated this session's identity map.
    appointment_type = await session.scalar(
        select(AppointmentType).where(AppointmentType.id == payload.appointment_type_id)
        .with_for_update(read=True).execution_options(populate_existing=True)
    )
    await session.execute(
        select(Doctor.id).where(Doctor.id == payload.doctor_id).with_for_update()
    )
    doctor = await directory_repo.get_doctor(session, payload.doctor_id)
    if doctor is None or not policies.doctor_is_published(doctor):
        raise NotFound("Doctor not found.")
    if appointment_type is None or not policies.type_applies_to_doctor(appointment_type, doctor):
        raise ValidationFailed("This appointment type is not offered by the selected doctor.")

    start = payload.start_time.astimezone(UTC)
    day = availability.local_day(start)
    availability.check_booking_window(day)

    # BR-03: revalidate at submission time, bypassing the browse cache.
    effective = resolve(doctor, appointment_type)
    slots = await availability.compute_slots(
        session, doctor.id, appointment_type, day, effective=effective
    )
    if not any(slot.start == start for slot in slots):
        BOOKINGS.labels(result="unavailable").inc()
        raise SlotTaken(
            "The selected time is not available. Please choose another time.",
            code="SlotUnavailable",
        )

    appointment = Appointment(
        booking_reference=generate_booking_reference(),
        patient_id=patient_id,
        doctor_id=doctor.id,
        appointment_type_id=appointment_type.id,
        start_time=start,
        end_time=start + effective.duration,
        end_with_buffer=start + effective.duration + effective.buffer,
        status=AppointmentStatus.PENDING,
        check_in_status=CheckInStatus.NOT_CHECKED_IN,
        reason_for_visit=payload.reason_for_visit,
        fee_amount=policies.effective_fee(doctor, appointment_type),
        currency=settings.currency,
    )
    doctor_id, erp_doctor_id = doctor.id, doctor.erp_doctor_id
    session.add(appointment)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if _is_overlap_violation(exc):
            BOOKINGS.labels(result="conflict").inc()
            raise SlotTaken() from exc
        raise

    appointment_repo.add_history(
        session,
        appointment.id,
        "status",
        None,
        AppointmentStatus.PENDING,
        "Booking request submitted",
        StatusSource.PATIENT,
    )
    audit.record(
        session,
        "appointment.created",
        "appointment",
        appointment.id,
        actor_id=user_id,
        details={"booking_reference": appointment.booking_reference, "doctor_id": doctor_id},
    )
    await notifications.notify_patient(  # FR-NOT-01
        session,
        patient_id,
        NotificationType.BOOKING_SUBMITTED,
        "Booking request submitted",
        f"Your booking request {appointment.booking_reference} for "
        f"{availability.format_local(start)} has been submitted and is awaiting confirmation.",
        f"/appointments/{appointment.id}",
    )
    await session.commit()
    await availability.invalidate(redis, doctor_id, day)

    await _submit_to_erp(session, erp, appointment, erp_doctor_id, patient_id)
    return appointment.id


async def _submit_to_erp(
    session: AsyncSession,
    erp: ErpAdapter,
    appointment: Appointment,
    erp_doctor_id: str | None,
    patient_id: int,
) -> None:
    if not erp_doctor_id:
        # Doctor not integrated: stays PENDING until handled (and reconciled/expired later).
        BOOKINGS.labels(result="pending").inc()
        return
    request = ErpBookingRequest(
        booking_reference=appointment.booking_reference,
        erp_doctor_id=erp_doctor_id,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        patient_ref=f"P{patient_id}",
    )
    try:
        result = await erp.create_booking(request)
    except ErpTimeoutError:
        # Outcome unknown: keep PENDING; erp_sync.reconcile_pending asks the ERP later.
        BOOKINGS.labels(result="pending").inc()
        logger.warning("erp_booking_timeout", appointment_id=appointment.id)
        return
    except ErpUnavailableError as exc:
        await transition(
            session,
            appointment,
            AppointmentStatus.REJECTED,
            reason="The hospital system was unavailable, so the booking could not be placed.",
            source=StatusSource.SYSTEM,
        )
        await session.commit()
        BOOKINGS.labels(result="erp_unavailable").inc()
        raise ErpUnavailable() from exc

    await apply_erp_result(session, appointment, result)
    await session.commit()
    BOOKINGS.labels(result=appointment.status.lower()).inc()


async def cancel_appointment(
    session: AsyncSession,
    redis: Redis,
    erp: ErpAdapter,
    gateway: PaymentGateway,
    patient: PatientProfile,
    appointment_id: int,
    reason: str | None,
) -> int:
    from app.services import payments as payment_service  # avoid import cycle

    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound("Appointment not found.")  # BR-12: do not reveal other patients' data
    if appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
        raise InvalidState("Only pending or confirmed appointments can be cancelled.")
    if not policies.can_cancel(appointment):
        raise InvalidState(
            "Appointments can only be cancelled at least "
            f"{settings.cancellation_cutoff_hours} hours "
            "before the start time.",
            code="CancellationWindowClosed",
        )

    if appointment.erp_booking_id:
        try:
            await erp.cancel_booking(appointment.erp_booking_id, reason)
        except ErpRejectedError as exc:
            raise InvalidState(str(exc), code="CancellationRejected") from exc
        except (ErpUnavailableError, ErpTimeoutError) as exc:
            raise ErpUnavailable() from exc

    await transition(
        session,
        appointment,
        AppointmentStatus.CANCELLED,
        reason=reason or "Cancelled by patient",
        source=StatusSource.PATIENT,
        actor_id=patient.user_id,
    )
    await session.commit()
    await availability.invalidate(
        redis, appointment.doctor_id, availability.local_day(appointment.start_time)
    )
    await payment_service.refund_if_paid(session, gateway, appointment)
    return appointment.id
