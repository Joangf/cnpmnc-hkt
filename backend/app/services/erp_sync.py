"""ERP/HIS synchronisation: schedule cache refresh, inbound status events, reconciliation."""

from datetime import UTC, datetime, time, timedelta

import structlog
from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, NotFound
from app.integrations.erp.base import ErpAdapter, ErpTimeoutError, ErpUnavailableError
from app.models import Appointment, Doctor, DoctorSchedule
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    AppointmentStatus,
    CheckInStatus,
    NotificationType,
    ScheduleSource,
    SchedulingMode,
    StatusSource,
)
from app.repositories import appointments as appointment_repo
from app.schemas.integrations import ErpEvent
from app.services import audit, availability, booking, notifications

logger = structlog.get_logger(__name__)


async def sync_schedules(session: AsyncSession, erp: ErpAdapter) -> bool:
    """Background-job entry point. Returns True if every doctor synced."""
    _, failures = await sync_all_schedules(session, erp)
    return failures == 0


async def sync_all_schedules(session: AsyncSession, erp: ErpAdapter) -> tuple[int, int]:
    """Replace the cached ERP schedule for every integrated doctor. Returns (synced, failed)."""
    tz = availability.clinic_tz()
    today = datetime.now(tz).date()
    end = today + timedelta(days=settings.booking_horizon_days)
    range_start = datetime.combine(today, time.min, tzinfo=tz)

    doctors = (
        await session.scalars(
            select(Doctor).where(Doctor.is_active.is_(True), Doctor.erp_doctor_id.is_not(None),
                                 Doctor.scheduling_mode == SchedulingMode.ERP)
        )
    ).all()
    failures = 0
    for doctor in doctors:
        assert doctor.erp_doctor_id is not None
        try:
            windows = await erp.get_schedule(doctor.erp_doctor_id, today, end)
        except (ErpUnavailableError, ErpTimeoutError):
            failures += 1
            logger.warning("schedule_sync_failed", doctor_id=doctor.id)
            continue
        # Serialize window replacement with local reservations; the ERP call above
        # deliberately happens before locking, so network I/O does not hold the lock.
        await session.execute(
            select(Doctor.id).where(Doctor.id == doctor.id).with_for_update()
        )
        # The mode may have changed while the ERP request was in flight.
        await session.refresh(doctor)
        if doctor.scheduling_mode != SchedulingMode.ERP:
            await session.commit()
            continue
        await session.execute(
            delete(DoctorSchedule).where(
                DoctorSchedule.doctor_id == doctor.id,
                DoctorSchedule.source == ScheduleSource.ERP,
                DoctorSchedule.start_time >= range_start,
            )
        )
        now = datetime.now(UTC)
        # Also versions availability cache entries when ERP windows/limits change.
        doctor.updated_at = now
        session.add_all(
            DoctorSchedule(
                doctor_id=doctor.id,
                start_time=w.start_time,
                end_time=w.end_time,
                max_appointments=w.max_appointments,
                is_available=w.is_available,
                source=ScheduleSource.ERP,
                synced_at=now,
            )
            for w in windows
        )
        await session.commit()
    logger.info("schedule_sync_completed", doctors=len(doctors), failures=failures)
    return len(doctors) - failures, failures


async def handle_event(session: AsyncSession, redis: Redis, event: ErpEvent) -> str:
    appointment = await appointment_repo.get_by_reference(session, event.booking_reference)
    if appointment is None:
        raise NotFound("Unknown booking reference.")
    if appointment.slot_id is not None:
        return "ignored"
    if event.erp_booking_id and appointment.erp_booking_id != event.erp_booking_id:
        appointment.erp_booking_id = event.erp_booking_id

    days = {availability.local_day(appointment.start_time)}
    if event.type == "APPOINTMENT_STATUS_CHANGED":
        new_status = booking.parse_status(event.status)
        if new_status is None:
            logger.warning("erp_event_unknown_status", status=event.status)
            return "ignored"
        changed = await booking.transition(
            session, appointment, new_status, reason=event.reason, source=StatusSource.ERP
        )
    elif event.type == "CHECK_IN_STATUS_CHANGED":
        changed = await _set_check_in_status(session, appointment, event.check_in_status)
    else:
        changed = await _reschedule(session, appointment, event)
        days.add(availability.local_day(appointment.start_time))

    await session.commit()
    if changed:
        await availability.invalidate(redis, appointment.doctor_id, *days)
    return "processed" if changed else "ignored"


async def _set_check_in_status(
    session: AsyncSession, appointment: Appointment, value: str | None
) -> bool:
    """BR-11: check-in status is only ever written from the ERP."""
    try:
        new_value = CheckInStatus(value) if value else None
    except ValueError:
        new_value = None
    if new_value is None or new_value == appointment.check_in_status:
        return False
    old_value = appointment.check_in_status
    appointment.check_in_status = new_value
    appointment_repo.add_history(
        session, appointment.id, "check_in_status", old_value, new_value, None, StatusSource.ERP
    )
    audit.record(
        session,
        "appointment.check_in_changed",
        "appointment",
        appointment.id,
        actor_type=audit.actor_type_for(StatusSource.ERP),
        details={"from": old_value, "to": new_value},
    )
    if new_value == CheckInStatus.CHECKED_IN:
        await notifications.notify_patient(
            session,
            appointment.patient_id,
            NotificationType.CHECK_IN,
            "Checked in",
            "The hospital has recorded your arrival for appointment "
            f"{appointment.booking_reference}.",
            f"/appointments/{appointment.id}",
        )
    return True


async def _reschedule(session: AsyncSession, appointment: Appointment, event: ErpEvent) -> bool:
    if event.start_time is None or event.end_time is None or event.end_time <= event.start_time:
        return False
    if appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
        return False
    # Old ERP references can outlive a switch to manual mode. Do not let a delayed
    # reschedule create a new future ERP interval inside an admin-managed schedule.
    mode = await session.scalar(select(Doctor.scheduling_mode).where(
        Doctor.id == appointment.doctor_id
    ).with_for_update())
    if mode != SchedulingMode.ERP:
        return False
    buffer = appointment.end_with_buffer - appointment.end_time
    old_start = appointment.start_time
    appointment.start_time = event.start_time.astimezone(UTC)
    appointment.end_time = event.end_time.astimezone(UTC)
    appointment.end_with_buffer = appointment.end_time + buffer
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        logger.error("erp_reschedule_conflict", booking_reference=event.booking_reference)
        raise Conflict("Rescheduled time overlaps another booking.", code="SlotTaken") from exc

    appointment_repo.add_history(
        session,
        appointment.id,
        "start_time",
        old_start.isoformat(),
        appointment.start_time.isoformat(),
        event.reason,
        StatusSource.ERP,
    )
    audit.record(
        session,
        "appointment.rescheduled",
        "appointment",
        appointment.id,
        actor_type=audit.actor_type_for(StatusSource.ERP),
        details={"from": old_start.isoformat(), "to": appointment.start_time.isoformat()},
    )
    await notifications.notify_patient(
        session,
        appointment.patient_id,
        NotificationType.APPOINTMENT_STATUS,
        "Appointment rescheduled",
        f"Appointment {appointment.booking_reference} has been moved to "
        f"{availability.format_local(appointment.start_time)}.",
        f"/appointments/{appointment.id}",
    )
    return True


async def reconcile_pending(session: AsyncSession, erp: ErpAdapter) -> bool:
    """Fallback poller: resolve PENDING bookings whose ERP outcome was never received."""
    now = datetime.now(UTC)
    expiry = now - timedelta(minutes=settings.pending_booking_expiry_minutes)
    for appointment in await appointment_repo.list_stale_pending(
        session, now - timedelta(seconds=30)
    ):
        try:
            result = await erp.get_booking(appointment.booking_reference)
        except (ErpUnavailableError, ErpTimeoutError):
            logger.warning("reconcile_erp_unavailable")
            await session.commit()
            return False
        if result is not None:
            await booking.apply_erp_result(session, appointment, result)
        elif appointment.created_at < expiry:
            await booking.transition(
                session,
                appointment,
                AppointmentStatus.REJECTED,
                reason="The hospital system did not receive this booking request.",
                source=StatusSource.SYSTEM,
            )
    await session.commit()
    return True
