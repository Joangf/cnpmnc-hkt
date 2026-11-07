"""Admin slot management and shared-capacity reservations.

All mutations acquire doctor then slot locks. Booking first locks its appointment type,
then uses the same doctor/slot order. ERP synchronization never owns these rows.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, NotFound, SlotTaken, ValidationFailed
from app.models import Appointment, Doctor, DoctorSlot
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, SchedulingMode
from app.schemas.slots import AdminSlotOut, SlotCreate, SlotUpdate
from app.services import audit
from app.services.scheduling import Slot


async def ensure_mode_change_allowed(session: AsyncSession, doctor: Doctor) -> None:
    exists = await session.scalar(select(Appointment.id).where(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.end_with_buffer > datetime.now(UTC),
    ).limit(1))
    if exists is not None:
        raise Conflict(
            "Resolve the doctor's upcoming or ongoing appointments "
            "before changing scheduling mode.",
            code="SchedulingModeInUse",
        )


async def lock_doctor(session: AsyncSession, doctor_id: int) -> Doctor:
    doctor = await session.scalar(select(Doctor).where(Doctor.id == doctor_id)
                                  .with_for_update().execution_options(populate_existing=True))
    if doctor is None:
        raise NotFound("Doctor not found.")
    return doctor


async def rows_for_day(
    session: AsyncSession, doctor_id: int, day: date
) -> list[tuple[DoctorSlot, int]]:
    from app.services.availability import day_bounds

    start, end = day_bounds(day)
    rows = await session.execute(
        select(DoctorSlot, func.count(Appointment.id))
        .outerjoin(Appointment, and_(
            Appointment.slot_id == DoctorSlot.id,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        ))
        .where(DoctorSlot.doctor_id == doctor_id, DoctorSlot.start_time >= start,
               DoctorSlot.start_time < end)
        .group_by(DoctorSlot.id).order_by(DoctorSlot.start_time)
    )
    return [(slot, int(count)) for slot, count in rows.all()]


def present(slot: DoctorSlot, booked: int) -> AdminSlotOut:
    return AdminSlotOut(
        id=slot.id, doctor_id=slot.doctor_id, start_time=slot.start_time,
        end_time=slot.end_time, buffer_minutes=slot.buffer_minutes, capacity=slot.capacity,
        is_open=slot.is_open, version=slot.version, booked_count=booked,
        remaining_places=max(0, slot.capacity - booked),
    )


def validate_timing(start: datetime, end: datetime, buffer: int) -> None:
    from app.services.availability import clinic_tz

    duration = end - start
    if not timedelta(minutes=5) <= duration <= timedelta(minutes=480):
        raise ValidationFailed("Slot duration must be between 5 and 480 minutes.")
    if any(moment.second or moment.microsecond for moment in (start, end)):
        raise ValidationFailed("Use whole-minute start and end times.")
    if start <= datetime.now(UTC):
        raise ValidationFailed("New slot times must be in the future.")
    local_start, local_end = start.astimezone(clinic_tz()), end.astimezone(clinic_tz())
    reserved_end = (end + timedelta(minutes=buffer)).astimezone(clinic_tz())
    if local_start.date() != local_end.date() or reserved_end.date() != local_start.date():
        raise ValidationFailed("The slot and its buffer must fit within one clinic-local date.")


async def _persist(session: AsyncSession, *, flush_only: bool = False) -> None:
    try:
        await (session.flush() if flush_only else session.commit())
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict(
            "This slot conflicts with an existing slot, including its buffer. "
            "Edit the existing slot or choose another time.", code="SlotConflict",
        ) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise Conflict(
            "The slot could not be saved. Previous settings remain effective; try again.",
            code="SlotWriteFailed",
        ) from exc


async def create(
    session: AsyncSession, doctor_id: int, payload: SlotCreate, actor_id: int
) -> AdminSlotOut:
    doctor = await lock_doctor(session, doctor_id)
    start, end = payload.start_time.astimezone(UTC), payload.end_time.astimezone(UTC)
    validate_timing(start, end, payload.buffer_minutes)
    slot = DoctorSlot(
        **payload.model_dump(exclude={"start_time", "end_time"}),
        doctor_id=doctor_id, start_time=start, end_time=end,
        end_with_buffer=end + timedelta(minutes=payload.buffer_minutes),
    )
    doctor.updated_at = datetime.now(UTC)
    session.add(slot)
    await _persist(session, flush_only=True)
    audit.record(session, "doctor_slot.created", "doctor_slot", slot.id, actor_id=actor_id)
    await _persist(session)
    return present(slot, 0)


async def update(
    session: AsyncSession, doctor_id: int, slot_id: int, payload: SlotUpdate, actor_id: int
) -> AdminSlotOut:
    doctor = await lock_doctor(session, doctor_id)
    slot = await session.scalar(select(DoctorSlot).where(
        DoctorSlot.id == slot_id, DoctorSlot.doctor_id == doctor_id,
    ).with_for_update().execution_options(populate_existing=True))
    if slot is None:
        raise NotFound("Slot not found for this doctor.")
    if slot.version != payload.version:
        raise Conflict("The slot changed. Refresh before saving again.", code="SlotChanged")
    booked = int(await session.scalar(select(func.count(Appointment.id)).where(
        Appointment.slot_id == slot.id, Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES)
    )) or 0)
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True, exclude={"version"}).items()
               if getattr(slot, k) != v}
    if {"start_time", "end_time", "buffer_minutes"}.intersection(changes):
        if booked:
            raise Conflict(
                "Booked slot times and buffer cannot change. Close it to stop new reservations.",
                code="SlotHasBookings",
            )
        validate_timing(changes.get("start_time", slot.start_time),
                        changes.get("end_time", slot.end_time),
                        changes.get("buffer_minutes", slot.buffer_minutes))
    if changes:
        for key, value in changes.items():
            setattr(slot, key, value)
        slot.end_with_buffer = slot.end_time + timedelta(minutes=slot.buffer_minutes)
        slot.version += 1
        doctor.updated_at = datetime.now(UTC)
        audit.record(session, "doctor_slot.updated", "doctor_slot", slot.id,
                     actor_id=actor_id, details={"fields": sorted(changes)})
        await _persist(session)
    return present(slot, booked)


async def offers(session: AsyncSession, doctor_id: int, day: date) -> list[Slot]:
    earliest = datetime.now(UTC) + timedelta(minutes=settings.booking_min_lead_minutes)
    return [
        Slot(slot.start_time, slot.end_time, slot.id, slot.version,
             slot.capacity, slot.capacity - booked)
        for slot, booked in await rows_for_day(session, doctor_id, day)
        if slot.is_open and slot.start_time >= earliest and booked < slot.capacity
    ]


async def reserve_position(
    session: AsyncSession, doctor: Doctor, slot_id: int | None, version: int | None,
    start: datetime, patient_id: int,
) -> tuple[DoctorSlot, int]:
    if slot_id is None or version is None:
        raise ValidationFailed("Select a manual slot and submit its current version.")
    slot = await session.scalar(select(DoctorSlot).where(
        DoctorSlot.id == slot_id, DoctorSlot.doctor_id == doctor.id,
    ).with_for_update().execution_options(populate_existing=True))
    if slot is None or slot.version != version or slot.start_time != start:
        raise SlotTaken(
            "The selected slot changed. Refresh and select it again.", code="SlotChanged"
        )
    earliest = datetime.now(UTC) + timedelta(minutes=settings.booking_min_lead_minutes)
    if (not slot.is_open or slot.start_time < earliest
            or doctor.scheduling_mode != SchedulingMode.MANUAL):
        raise SlotTaken("This slot is no longer open for bookings.", code="SlotUnavailable")
    occupied = (await session.execute(select(
        Appointment.patient_id, Appointment.reservation_position,
    ).where(Appointment.slot_id == slot.id,
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES)))).all()
    if any(patient == patient_id for patient, _ in occupied):
        raise Conflict("You already have a reservation in this slot.", code="AlreadyBooked")
    if len(occupied) >= slot.capacity:
        raise SlotTaken("This slot is full. Please choose another slot.", code="SlotFull")
    positions = {position for _, position in occupied}
    # At most len(occupied)+1 probes, even when the configured capacity is very large.
    position = next(i for i in range(1, len(occupied) + 2) if i not in positions)
    return slot, position
