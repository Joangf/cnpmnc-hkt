from datetime import datetime
from typing import Literal

from sqlalchemy import not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Appointment,
    AppointmentStatusHistory,
    Department,
    Doctor,
    DoctorSchedule,
)
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus, StatusSource
from app.repositories.base import paginate

Scope = Literal["upcoming", "past", "all"]


def summary_options() -> tuple:
    return (
        joinedload(Appointment.doctor).joinedload(Doctor.hospital),
        joinedload(Appointment.doctor)
        .joinedload(Doctor.department)
        .joinedload(Department.specialty),
        joinedload(Appointment.appointment_type),
        selectinload(Appointment.payments),
    )


def detail_options() -> tuple:
    return (
        *summary_options(),
        selectinload(Appointment.history),
        selectinload(Appointment.review),
    )


async def get_detail(session: AsyncSession, appointment_id: int) -> Appointment | None:
    stmt = (
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(*detail_options())
        .execution_options(populate_existing=True)
    )
    return (await session.scalars(stmt)).unique().one_or_none()


async def get_by_reference(session: AsyncSession, booking_reference: str) -> Appointment | None:
    stmt = (
        select(Appointment)
        .where(Appointment.booking_reference == booking_reference)
        .options(*detail_options())
        .execution_options(populate_existing=True)
    )
    return (await session.scalars(stmt)).unique().one_or_none()


async def list_for_patient(
    session: AsyncSession, patient_id: int, scope: Scope, now: datetime, page: int, page_size: int
) -> tuple[list[Appointment], int]:
    stmt = (
        select(Appointment).where(Appointment.patient_id == patient_id).options(*summary_options())
    )
    active = Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES)
    if scope == "upcoming":
        stmt = stmt.where(Appointment.start_time >= now, active).order_by(
            Appointment.start_time.asc()
        )
    elif scope == "past":
        stmt = stmt.where(or_(Appointment.start_time < now, not_(active))).order_by(
            Appointment.start_time.desc()
        )
    else:
        stmt = stmt.order_by(Appointment.start_time.desc())
    return await paginate(session, stmt, page, page_size)


async def list_admin(
    session: AsyncSession,
    *,
    status: AppointmentStatus | None,
    doctor_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[Appointment], int]:
    stmt = select(Appointment).options(*summary_options()).order_by(Appointment.start_time.desc())
    if status:
        stmt = stmt.where(Appointment.status == status)
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if date_from:
        stmt = stmt.where(Appointment.start_time >= date_from)
    if date_to:
        stmt = stmt.where(Appointment.start_time < date_to)
    return await paginate(session, stmt, page, page_size)


async def busy_intervals(
    session: AsyncSession, doctor_id: int, start: datetime, end: datetime
) -> list[tuple[datetime, datetime]]:
    """[start_time, end_with_buffer) of every slot-holding appointment overlapping the range."""
    stmt = select(Appointment.start_time, Appointment.end_with_buffer).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.start_time < end,
        Appointment.end_with_buffer > start,
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]


async def schedule_rows(
    session: AsyncSession, doctor_id: int, start: datetime, end: datetime
) -> list[DoctorSchedule]:
    stmt = (
        select(DoctorSchedule)
        .where(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.start_time < end,
            DoctorSchedule.end_time > start,
        )
        .order_by(DoctorSchedule.start_time)
    )
    return list((await session.scalars(stmt)).all())


async def list_stale_pending(
    session: AsyncSession, created_before: datetime, limit: int = 100
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .where(
            Appointment.status == AppointmentStatus.PENDING, Appointment.created_at < created_before
        )
        .order_by(Appointment.created_at)
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


def add_history(
    session: AsyncSession,
    appointment_id: int,
    field: str,
    from_value: str | None,
    to_value: str,
    reason: str | None,
    source: StatusSource,
) -> None:
    session.add(
        AppointmentStatusHistory(
            appointment_id=appointment_id,
            field=field,
            from_value=from_value,
            to_value=to_value,
            reason=reason[:500] if reason else None,
            source=source,
        )
    )
