from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import AppointmentType, Department, Doctor, DoctorSchedule, Hospital, Specialty
from app.models.enums import DepartmentVisibility, FacilityType
from app.repositories.base import paginate


def _hospital_options() -> tuple:
    return (selectinload(Hospital.departments).joinedload(Department.specialty),)


def _doctor_options() -> tuple:
    return (
        joinedload(Doctor.hospital),
        joinedload(Doctor.department).joinedload(Department.specialty),
    )


def _published_doctor() -> ColumnElement[bool]:
    """SQL form of `policies.doctor_is_published`."""
    return and_(
        Doctor.is_active.is_(True),
        Doctor.hospital.has(Hospital.is_active.is_(True)),
        Doctor.department.has(
            and_(
                Department.is_active.is_(True),
                Department.specialty.has(Specialty.is_active.is_(True)),
            )
        ),
    )


async def list_specialties(
    session: AsyncSession, *, include_inactive: bool = False
) -> list[Specialty]:
    stmt = select(Specialty).order_by(Specialty.name)
    if not include_inactive:
        stmt = stmt.where(Specialty.is_active.is_(True))
    return list((await session.scalars(stmt)).all())


async def list_hospitals(
    session: AsyncSession,
    *,
    q: str | None = None,
    city: str | None = None,
    specialty_id: int | None = None,
    facility_type: FacilityType | None = None,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Hospital], int]:
    stmt = select(Hospital).options(*_hospital_options()).order_by(Hospital.name)
    if not include_inactive:
        stmt = stmt.where(Hospital.is_active.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Hospital.name.ilike(like), Hospital.address.ilike(like), Hospital.city.ilike(like))
        )
    if city:
        stmt = stmt.where(Hospital.city.ilike(city))
    if facility_type:
        stmt = stmt.where(Hospital.facility_type == facility_type)
    if specialty_id:
        stmt = stmt.where(
            Hospital.departments.any(
                and_(
                    Department.specialty_id == specialty_id,
                    Department.is_active.is_(True),
                    Department.visibility == DepartmentVisibility.PUBLIC,
                    Department.specialty.has(Specialty.is_active.is_(True)),
                )
            )
        )
    return await paginate(session, stmt, page, page_size)


async def get_hospital(session: AsyncSession, hospital_id: int) -> Hospital | None:
    stmt = (
        select(Hospital)
        .where(Hospital.id == hospital_id)
        .options(*_hospital_options())
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


def _public_department_options() -> tuple:
    return (
        joinedload(Department.hospital),
        joinedload(Department.specialty),
        selectinload(Department.doctors).joinedload(Doctor.hospital),
        selectinload(Department.doctors)
        .joinedload(Doctor.department)
        .joinedload(Department.specialty),
    )


async def list_public_departments(
    session: AsyncSession,
    *,
    q: str | None = None,
    hospital_id: int | None = None,
    specialty_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Department], int]:
    """Published departments/clinics only: active, PUBLIC and under an active facility."""
    stmt = (
        select(Department)
        .where(
            Department.is_active.is_(True),
            Department.visibility == DepartmentVisibility.PUBLIC,
            Department.hospital.has(Hospital.is_active.is_(True)),
            Department.specialty.has(Specialty.is_active.is_(True)),
        )
        .options(*_public_department_options())
        .order_by(Department.name, Department.id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Department.name.ilike(like),
                Department.description.ilike(like),
                Department.location.ilike(like),
                Department.hospital.has(Hospital.name.ilike(like)),
                Department.specialty.has(Specialty.name.ilike(like)),
            )
        )
    if hospital_id:
        stmt = stmt.where(Department.hospital_id == hospital_id)
    if specialty_id:
        stmt = stmt.where(Department.specialty_id == specialty_id)
    return await paginate(session, stmt, page, page_size)


async def get_public_department(session: AsyncSession, department_id: int) -> Department | None:
    stmt = (
        select(Department)
        .where(
            Department.id == department_id,
            Department.is_active.is_(True),
            Department.visibility == DepartmentVisibility.PUBLIC,
            Department.hospital.has(Hospital.is_active.is_(True)),
            Department.specialty.has(Specialty.is_active.is_(True)),
        )
        .options(*_public_department_options())
    )
    return await session.scalar(stmt)


async def list_departments(
    session: AsyncSession, *, hospital_id: int | None = None, include_inactive: bool = False
) -> list[Department]:
    stmt = (
        select(Department)
        .options(joinedload(Department.specialty))
        .order_by(Department.hospital_id, Department.name)
    )
    if hospital_id:
        stmt = stmt.where(Department.hospital_id == hospital_id)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    return list((await session.scalars(stmt)).all())


async def get_department(session: AsyncSession, department_id: int) -> Department | None:
    stmt = (
        select(Department)
        .where(Department.id == department_id)
        .options(joinedload(Department.specialty))
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def departments_for_specialties(
    session: AsyncSession, specialty_ids: Sequence[int]
) -> list[Department]:
    if not specialty_ids:
        return []
    stmt = (
        select(Department)
        .join(Department.hospital)
        .where(
            Department.specialty_id.in_(specialty_ids),
            Department.is_active.is_(True),
            Department.visibility == DepartmentVisibility.PUBLIC,
            Hospital.is_active.is_(True),
        )
        .options(joinedload(Department.hospital), joinedload(Department.specialty))
        .order_by(Hospital.name)
    )
    return list((await session.scalars(stmt)).unique().all())


async def list_doctors(
    session: AsyncSession,
    *,
    q: str | None = None,
    hospital_id: int | None = None,
    department_id: int | None = None,
    specialty_id: int | None = None,
    available_from: datetime | None = None,
    available_to: datetime | None = None,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Doctor], int]:
    stmt = select(Doctor).options(*_doctor_options()).order_by(Doctor.full_name)
    if not include_inactive:
        stmt = stmt.where(_published_doctor())
    if q:
        stmt = stmt.where(Doctor.full_name.ilike(f"%{q}%"))
    if hospital_id:
        stmt = stmt.where(Doctor.hospital_id == hospital_id)
    if department_id:
        stmt = stmt.where(Doctor.department_id == department_id)
    if specialty_id:
        stmt = stmt.where(
            Doctor.department_id.in_(
                select(Department.id).where(Department.specialty_id == specialty_id)
            )
        )
    if available_from or available_to:
        # Doctor has an open schedule window overlapping [available_from, available_to].
        window = [DoctorSchedule.doctor_id == Doctor.id, DoctorSchedule.is_available.is_(True)]
        if available_from:
            window.append(DoctorSchedule.end_time > available_from)
        if available_to:
            window.append(DoctorSchedule.start_time < available_to)
        stmt = stmt.where(select(DoctorSchedule.id).where(*window).exists())
    return await paginate(session, stmt, page, page_size)


async def get_doctor(session: AsyncSession, doctor_id: int) -> Doctor | None:
    stmt = (
        select(Doctor)
        .where(Doctor.id == doctor_id)
        .options(*_doctor_options())
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def list_appointment_types_for_doctor(
    session: AsyncSession, doctor: Doctor
) -> list[AppointmentType]:
    specialty_id = doctor.department.specialty_id
    stmt = (
        select(AppointmentType)
        .where(
            AppointmentType.is_active.is_(True),
            or_(
                AppointmentType.doctor_id == doctor.id,
                and_(
                    AppointmentType.doctor_id.is_(None),
                    or_(
                        AppointmentType.specialty_id.is_(None),
                        AppointmentType.specialty_id == specialty_id,
                    ),
                ),
            ),
        )
        .order_by(AppointmentType.duration_minutes, AppointmentType.name)
    )
    return list((await session.scalars(stmt)).all())


async def list_appointment_types(session: AsyncSession) -> list[AppointmentType]:
    stmt = select(AppointmentType).order_by(AppointmentType.name)
    return list((await session.scalars(stmt)).all())
