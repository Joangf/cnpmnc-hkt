"""Administration (FRD 4.13). Every route requires the ADMIN role (BR-13); mutations are audited."""

from datetime import date, datetime, time
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import presenters
from app.api.deps import AdminUser, ErpDep, PageDep, SessionDep
from app.core.errors import Conflict, InvalidState, NotFound, ValidationFailed
from app.models import AppointmentType, AuditLog, Base, Department, Doctor, Hospital, Specialty
from app.models.enums import AccountStatus, AppointmentStatus, ReviewStatus, UserRole
from app.repositories import appointments as appointment_repo
from app.repositories import directory as directory_repo
from app.repositories import reviews as review_repo
from app.repositories import users as user_repo
from app.repositories.base import paginate
from app.schemas.admin import (
    AdminUserOut,
    AppointmentTypeAdminOut,
    AppointmentTypeCreate,
    AppointmentTypeUpdate,
    AuditLogOut,
    DepartmentCreate,
    DepartmentUpdate,
    DoctorCreate,
    DoctorUpdate,
    HospitalCreate,
    HospitalUpdate,
    ReportSummary,
    ScheduleSyncResult,
    SpecialtyCreate,
    SpecialtyUpdate,
    UserStatusUpdate,
)
from app.schemas.appointments import AdminAppointmentOut
from app.schemas.common import Page, error_responses
from app.schemas.directory import DepartmentOut, DoctorDetail, HospitalDetail, SpecialtyOut
from app.schemas.reviews import AdminReviewOut, ReviewModerate
from app.services import audit, availability, erp_sync, reports
from app.services import reviews as review_service

router = APIRouter(prefix="/admin", tags=["admin"], responses=error_responses(401, 403))


def _apply_changes(entity: Any, payload: BaseModel) -> list[str]:
    """Copy explicitly-set fields onto the entity; reject nulls for NOT NULL columns."""
    columns = entity.__table__.columns
    changed: list[str] = []
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and not columns[field].nullable:
            raise ValidationFailed(f"'{field}' cannot be empty.")
        if getattr(entity, field) != value:
            setattr(entity, field, value)
            changed.append(field)
    return changed


async def _require_ref(session: AsyncSession, model: type[Base], ref_id: int, label: str) -> Any:
    """Resolve an id given in the request body; an unknown id is invalid input (422), not a 404."""
    entity = await session.get(model, ref_id)
    if entity is None:
        raise ValidationFailed(f"{label} #{ref_id} does not exist.", code="InvalidReference")
    return entity


_WRITE_REJECTED = (
    "The change was rejected because it conflicts with existing data "
    "(for example a duplicate name or identifier). Refresh and try again."
)


async def _commit(
    session: AsyncSession,
    *,
    flush_only: bool = False,
    message: str = _WRITE_REJECTED,
    code: str = "WriteRejected",
) -> None:
    """Flush or commit, turning a constraint violation (e.g. a concurrent duplicate that slipped
    past the pre-checks) into a 409 the admin can act on instead of a 500."""
    try:
        await (session.flush() if flush_only else session.commit())
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict(message, code=code) from exc


async def _ensure_unique_specialty_name(
    session: AsyncSession, name: str, exclude_id: int | None = None
) -> None:
    stmt = select(Specialty.id).where(func.lower(Specialty.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Specialty.id != exclude_id)
    if await session.scalar(stmt):
        raise Conflict(f"A specialty named '{name}' already exists.", code="DuplicateName")


async def _ensure_unique_erp_doctor_id(
    session: AsyncSession, erp_doctor_id: str | None, exclude_id: int | None = None
) -> None:
    if erp_doctor_id is None:
        return
    stmt = select(Doctor.id).where(Doctor.erp_doctor_id == erp_doctor_id)
    if exclude_id is not None:
        stmt = stmt.where(Doctor.id != exclude_id)
    if (other := await session.scalar(stmt)) is not None:
        raise Conflict(
            f"ERP doctor ID '{erp_doctor_id}' is already linked to doctor #{other}.",
            code="DuplicateIdentifier",
        )


def _local_start(day: date | None) -> datetime | None:
    return datetime.combine(day, time.min, tzinfo=availability.clinic_tz()) if day else None


# --- Users (FR-ACC-05, FR-ADM-03) -------------------------------------------------------------


@router.get("/users", response_model=Page[AdminUserOut], operation_id="adminListUsers")
async def list_users(
    admin: AdminUser,
    session: SessionDep,
    paging: PageDep,
    q: str | None = None,
    role: UserRole | None = None,
    account_status: AccountStatus | None = None,
) -> Page[AdminUserOut]:
    users, total = await user_repo.list_users(
        session,
        q=q,
        role=role,
        account_status=account_status,
        page=paging.page,
        page_size=paging.page_size,
    )
    return Page[AdminUserOut](
        items=[presenters.admin_user(u) for u in users],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    operation_id="adminUpdateUserStatus",
    responses=error_responses(404, 409),
)
async def update_user_status(
    user_id: int, payload: UserStatusUpdate, admin: AdminUser, session: SessionDep
) -> AdminUserOut:
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise NotFound("User not found.")
    if user.id == admin.id:
        raise InvalidState("You cannot change the status of your own account.")
    if user.account_status != payload.account_status:
        old = user.account_status
        user.account_status = payload.account_status
        audit.record(
            session,
            "user.status_changed",
            "user",
            user.id,
            actor_id=admin.id,
            details={"from": old, "to": payload.account_status},
        )
        await session.commit()
    return presenters.admin_user(user)


# --- Specialties ------------------------------------------------------------------------------


@router.get("/specialties", response_model=list[SpecialtyOut], operation_id="adminListSpecialties")
async def admin_list_specialties(admin: AdminUser, session: SessionDep) -> list[SpecialtyOut]:
    items = await directory_repo.list_specialties(session, include_inactive=True)
    return [SpecialtyOut.model_validate(s) for s in items]


@router.post(
    "/specialties",
    status_code=status.HTTP_201_CREATED,
    response_model=SpecialtyOut,
    operation_id="adminCreateSpecialty",
    responses=error_responses(409, 422),
)
async def create_specialty(
    payload: SpecialtyCreate, admin: AdminUser, session: SessionDep
) -> SpecialtyOut:
    await _ensure_unique_specialty_name(session, payload.name)
    specialty = Specialty(**payload.model_dump())
    session.add(specialty)
    await _commit(
        session,
        flush_only=True,
        message="A specialty with this name already exists.",
        code="DuplicateName",
    )
    audit.record(session, "specialty.created", "specialty", specialty.id, actor_id=admin.id)
    await _commit(session)
    return SpecialtyOut.model_validate(specialty)


@router.patch(
    "/specialties/{specialty_id}",
    response_model=SpecialtyOut,
    operation_id="adminUpdateSpecialty",
    responses=error_responses(404, 409, 422),
)
async def update_specialty(
    specialty_id: int, payload: SpecialtyUpdate, admin: AdminUser, session: SessionDep
) -> SpecialtyOut:
    specialty = await session.get(Specialty, specialty_id)
    if specialty is None:
        raise NotFound("Specialty not found.")
    if payload.name is not None:
        await _ensure_unique_specialty_name(session, payload.name, exclude_id=specialty.id)
    if changed := _apply_changes(specialty, payload):
        audit.record(
            session,
            "specialty.updated",
            "specialty",
            specialty.id,
            actor_id=admin.id,
            details={"fields": changed},
        )
        await _commit(session)
    return SpecialtyOut.model_validate(specialty)


# --- Hospitals --------------------------------------------------------------------------------


@router.get("/hospitals", response_model=list[HospitalDetail], operation_id="adminListHospitals")
async def admin_list_hospitals(admin: AdminUser, session: SessionDep) -> list[HospitalDetail]:
    items, _ = await directory_repo.list_hospitals(
        session, include_inactive=True, page=1, page_size=1000
    )
    return [presenters.hospital_detail(h, include_inactive=True) for h in items]


@router.post(
    "/hospitals",
    status_code=status.HTTP_201_CREATED,
    response_model=HospitalDetail,
    operation_id="adminCreateHospital",
    responses=error_responses(422),
)
async def create_hospital(
    payload: HospitalCreate, admin: AdminUser, session: SessionDep
) -> HospitalDetail:
    hospital = Hospital(**payload.model_dump())
    session.add(hospital)
    await session.flush()
    audit.record(session, "hospital.created", "hospital", hospital.id, actor_id=admin.id)
    await session.commit()
    loaded = await directory_repo.get_hospital(session, hospital.id)
    assert loaded is not None
    return presenters.hospital_detail(loaded, include_inactive=True)


@router.patch(
    "/hospitals/{hospital_id}",
    response_model=HospitalDetail,
    operation_id="adminUpdateHospital",
    responses=error_responses(404, 422),
)
async def update_hospital(
    hospital_id: int, payload: HospitalUpdate, admin: AdminUser, session: SessionDep
) -> HospitalDetail:
    hospital = await directory_repo.get_hospital(session, hospital_id)
    if hospital is None:
        raise NotFound("Hospital not found.")
    if changed := _apply_changes(hospital, payload):
        audit.record(
            session,
            "hospital.updated",
            "hospital",
            hospital.id,
            actor_id=admin.id,
            details={"fields": changed},
        )
        await session.commit()
    return presenters.hospital_detail(hospital, include_inactive=True)


# --- Departments ------------------------------------------------------------------------------


@router.get("/departments", response_model=list[DepartmentOut], operation_id="adminListDepartments")
async def admin_list_departments(
    admin: AdminUser, session: SessionDep, hospital_id: int | None = None
) -> list[DepartmentOut]:
    items = await directory_repo.list_departments(
        session, hospital_id=hospital_id, include_inactive=True
    )
    return [presenters.department_out(d) for d in items]


@router.post(
    "/departments",
    status_code=status.HTTP_201_CREATED,
    response_model=DepartmentOut,
    operation_id="adminCreateDepartment",
    responses=error_responses(409, 422),
)
async def create_department(
    payload: DepartmentCreate, admin: AdminUser, session: SessionDep
) -> DepartmentOut:
    await _require_ref(session, Hospital, payload.hospital_id, "Hospital")
    await _require_ref(session, Specialty, payload.specialty_id, "Specialty")
    department = Department(**payload.model_dump())
    session.add(department)
    await session.flush()
    audit.record(session, "department.created", "department", department.id, actor_id=admin.id)
    await _commit(session)
    loaded = await directory_repo.get_department(session, department.id)
    assert loaded is not None
    return presenters.department_out(loaded)


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentOut,
    operation_id="adminUpdateDepartment",
    responses=error_responses(404, 409, 422),
)
async def update_department(
    department_id: int, payload: DepartmentUpdate, admin: AdminUser, session: SessionDep
) -> DepartmentOut:
    department = await directory_repo.get_department(session, department_id)
    if department is None:
        raise NotFound("Department not found.")
    if payload.specialty_id is not None:
        await _require_ref(session, Specialty, payload.specialty_id, "Specialty")
    if changed := _apply_changes(department, payload):
        audit.record(
            session,
            "department.updated",
            "department",
            department.id,
            actor_id=admin.id,
            details={"fields": changed},
        )
        await _commit(session)
    loaded = await directory_repo.get_department(session, department_id)
    assert loaded is not None
    return presenters.department_out(loaded)


# --- Doctors ----------------------------------------------------------------------------------


@router.get("/doctors", response_model=list[DoctorDetail], operation_id="adminListDoctors")
async def admin_list_doctors(
    admin: AdminUser, session: SessionDep, hospital_id: int | None = None
) -> list[DoctorDetail]:
    items, _ = await directory_repo.list_doctors(
        session, hospital_id=hospital_id, include_inactive=True, page=1, page_size=1000
    )
    return [presenters.doctor_detail(d) for d in items]


@router.post(
    "/doctors",
    status_code=status.HTTP_201_CREATED,
    response_model=DoctorDetail,
    operation_id="adminCreateDoctor",
    responses=error_responses(409, 422),
)
async def create_doctor(
    payload: DoctorCreate, admin: AdminUser, session: SessionDep
) -> DoctorDetail:
    department = await _require_ref(session, Department, payload.department_id, "Department")
    await _ensure_unique_erp_doctor_id(session, payload.erp_doctor_id)
    doctor = Doctor(**payload.model_dump(), hospital_id=department.hospital_id)
    session.add(doctor)
    await _commit(
        session,
        flush_only=True,
        message="This ERP doctor ID is already linked to another doctor.",
        code="DuplicateIdentifier",
    )
    audit.record(session, "doctor.created", "doctor", doctor.id, actor_id=admin.id)
    await _commit(session)
    loaded = await directory_repo.get_doctor(session, doctor.id)
    assert loaded is not None
    return presenters.doctor_detail(loaded)


@router.patch(
    "/doctors/{doctor_id}",
    response_model=DoctorDetail,
    operation_id="adminUpdateDoctor",
    responses=error_responses(404, 409, 422),
)
async def update_doctor(
    doctor_id: int, payload: DoctorUpdate, admin: AdminUser, session: SessionDep
) -> DoctorDetail:
    doctor = await directory_repo.get_doctor(session, doctor_id)
    if doctor is None:
        raise NotFound("Doctor not found.")
    if payload.department_id is not None:
        department = await _require_ref(session, Department, payload.department_id, "Department")
        doctor.hospital_id = department.hospital_id
    await _ensure_unique_erp_doctor_id(session, payload.erp_doctor_id, exclude_id=doctor.id)
    if changed := _apply_changes(doctor, payload):
        audit.record(
            session,
            "doctor.updated",
            "doctor",
            doctor.id,
            actor_id=admin.id,
            details={"fields": changed},
        )
        await _commit(session)
    loaded = await directory_repo.get_doctor(session, doctor_id)
    assert loaded is not None
    return presenters.doctor_detail(loaded)


# --- Appointment types (BR-05) ----------------------------------------------------------------


@router.get(
    "/appointment-types",
    response_model=list[AppointmentTypeAdminOut],
    operation_id="adminListAppointmentTypes",
)
async def admin_list_appointment_types(
    admin: AdminUser, session: SessionDep
) -> list[AppointmentTypeAdminOut]:
    return [
        presenters.appointment_type_admin(t)
        for t in await directory_repo.list_appointment_types(session)
    ]


async def _validate_type_scope(
    session: AsyncSession, specialty_id: int | None, doctor_id: int | None
) -> None:
    if specialty_id is not None and await session.get(Specialty, specialty_id) is None:
        raise NotFound("Specialty not found.")
    if doctor_id is not None and await session.get(Doctor, doctor_id) is None:
        raise NotFound("Doctor not found.")


@router.post(
    "/appointment-types",
    status_code=status.HTTP_201_CREATED,
    response_model=AppointmentTypeAdminOut,
    operation_id="adminCreateAppointmentType",
    responses=error_responses(404, 422),
)
async def create_appointment_type(
    payload: AppointmentTypeCreate, admin: AdminUser, session: SessionDep
) -> AppointmentTypeAdminOut:
    await _validate_type_scope(session, payload.specialty_id, payload.doctor_id)
    appointment_type = AppointmentType(**payload.model_dump())
    session.add(appointment_type)
    await session.flush()
    audit.record(
        session,
        "appointment_type.created",
        "appointment_type",
        appointment_type.id,
        actor_id=admin.id,
    )
    await session.commit()
    return presenters.appointment_type_admin(appointment_type)


@router.patch(
    "/appointment-types/{type_id}",
    response_model=AppointmentTypeAdminOut,
    operation_id="adminUpdateAppointmentType",
    responses=error_responses(404, 422),
)
async def update_appointment_type(
    type_id: int, payload: AppointmentTypeUpdate, admin: AdminUser, session: SessionDep
) -> AppointmentTypeAdminOut:
    appointment_type = await session.get(AppointmentType, type_id)
    if appointment_type is None:
        raise NotFound("Appointment type not found.")
    await _validate_type_scope(session, payload.specialty_id, payload.doctor_id)
    if changed := _apply_changes(appointment_type, payload):
        audit.record(
            session,
            "appointment_type.updated",
            "appointment_type",
            appointment_type.id,
            actor_id=admin.id,
            details={"fields": changed},
        )
        await session.commit()
    return presenters.appointment_type_admin(appointment_type)


# --- Reviews (FR-REV-05, FR-ADM-04) -----------------------------------------------------------


@router.get("/reviews", response_model=Page[AdminReviewOut], operation_id="adminListReviews")
async def admin_list_reviews(
    admin: AdminUser,
    session: SessionDep,
    paging: PageDep,
    review_status: ReviewStatus | None = None,
    doctor_id: int | None = None,
) -> Page[AdminReviewOut]:
    items, total = await review_repo.list_admin(
        session,
        status=review_status,
        doctor_id=doctor_id,
        page=paging.page,
        page_size=paging.page_size,
    )
    return Page[AdminReviewOut](
        items=[presenters.admin_review(r) for r in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.patch(
    "/reviews/{review_id}",
    response_model=AdminReviewOut,
    operation_id="adminModerateReview",
    responses=error_responses(404, 422),
)
async def moderate_review(
    review_id: int, payload: ReviewModerate, admin: AdminUser, session: SessionDep
) -> AdminReviewOut:
    review = await review_service.moderate(
        session, admin, review_id, ReviewStatus(payload.status), payload.note
    )
    return presenters.admin_review(review)


# --- Appointments, reports, audit (FR-ADM-05/06, FR-RPT) ---------------------------------------


@router.get(
    "/appointments", response_model=Page[AdminAppointmentOut], operation_id="adminListAppointments"
)
async def admin_list_appointments(
    admin: AdminUser,
    session: SessionDep,
    paging: PageDep,
    appointment_status: AppointmentStatus | None = None,
    doctor_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AdminAppointmentOut]:
    items, total = await appointment_repo.list_admin(
        session,
        status=appointment_status,
        doctor_id=doctor_id,
        date_from=_local_start(date_from),
        date_to=_local_start(date_to),
        page=paging.page,
        page_size=paging.page_size,
    )
    return Page[AdminAppointmentOut](
        items=[presenters.admin_appointment(a) for a in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get("/reports/summary", response_model=ReportSummary, operation_id="adminGetReportSummary")
async def report_summary(
    admin: AdminUser,
    session: SessionDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ReportSummary:
    return await reports.summary(session, _local_start(date_from), _local_start(date_to))


@router.get("/audit-logs", response_model=Page[AuditLogOut], operation_id="adminListAuditLogs")
async def list_audit_logs(
    admin: AdminUser,
    session: SessionDep,
    paging: PageDep,
    entity_type: str | None = None,
    action: str | None = None,
) -> Page[AuditLogOut]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    items, total = await paginate(session, stmt, paging.page, paging.page_size)
    return Page[AuditLogOut](
        items=[AuditLogOut.model_validate(i) for i in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.post(
    "/integrations/erp/sync-schedules",
    response_model=ScheduleSyncResult,
    operation_id="adminSyncSchedules",
    responses=error_responses(503),
)
async def sync_schedules(admin: AdminUser, session: SessionDep, erp: ErpDep) -> ScheduleSyncResult:
    synced, failed = await erp_sync.sync_all_schedules(session, erp)
    audit.record(
        session,
        "erp.schedule_sync",
        "doctor_schedule",
        None,
        actor_id=admin.id,
        details={"synced": synced, "failed": failed},
    )
    await session.commit()
    return ScheduleSyncResult(doctors_synced=synced, success=failed == 0)
