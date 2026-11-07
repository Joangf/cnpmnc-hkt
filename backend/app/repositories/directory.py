from collections.abc import Sequence

from sqlalchemy import and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import AppointmentType, Department, Doctor, Hospital, Specialty
from app.models.enums import FacilityType
from app.repositories.base import paginate


def _hospital_options() -> tuple:
    return (selectinload(Hospital.departments).joinedload(Department.specialty),)


def _doctor_options() -> tuple:
    return (
        joinedload(Doctor.hospital),
        joinedload(Doctor.department).joinedload(Department.specialty),
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
                and_(Department.specialty_id == specialty_id, Department.is_active.is_(True))
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
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Doctor], int]:
    stmt = select(Doctor).options(*_doctor_options()).order_by(Doctor.full_name)
    if not include_inactive:
        stmt = stmt.where(Doctor.is_active.is_(True))
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
        .order_by(
            case(
                (AppointmentType.name.ilike("%standard%"), 0),
                (AppointmentType.name.ilike("%tiêu chuẩn%"), 0),
                (AppointmentType.name.ilike("%thường%"), 0),
                (AppointmentType.name.ilike("%follow-up%"), 3),
                (AppointmentType.name.ilike("%tái khám%"), 3),
                (AppointmentType.name.ilike("%extended%"), 2),
                (AppointmentType.name.ilike("%chuyên sâu%"), 2),
                else_=1,
            ),
            AppointmentType.duration_minutes,
            AppointmentType.name,
        )
    )
    return list((await session.scalars(stmt)).all())


async def list_appointment_types(session: AsyncSession) -> list[AppointmentType]:
    stmt = select(AppointmentType).order_by(AppointmentType.name)
    return list((await session.scalars(stmt)).all())
