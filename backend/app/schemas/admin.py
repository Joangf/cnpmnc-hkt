from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import (
    AccountStatus,
    ActorType,
    DepartmentVisibility,
    FacilityType,
    PaymentStatus,
    SchedulingMode,
    UserRole,
)
from app.schemas.common import ORMModel
from app.schemas.directory import AppointmentTypeOut, DepartmentOut, DoctorDetail
from app.schemas.validators import LongText, Name, ShortText, bounded

# Bounds mirror the columns in app/models/directory.py.
SpecialtyName = Annotated[str, bounded(100, 1)]
DepartmentName = Annotated[str, bounded(150, 1)]
DoctorName = Annotated[str, bounded(150, 1)]
DoctorTitle = Annotated[str, bounded(100)]
Url = Annotated[str, bounded(500)]
WebUrl = Annotated[str, bounded(255)]
Address = Annotated[str, bounded(255, 1)]
City = Annotated[str, bounded(100, 1)]
FacilityPhone = Annotated[str, bounded(30)]
# External identifier: unique when set, so an empty string is rejected rather than stored.
ErpDoctorId = Annotated[str, bounded(64, 1)]
Capacity = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
Duration = Annotated[int, Field(strict=True, ge=5, le=480)]
Buffer = Annotated[int, Field(strict=True, ge=0, le=120)]
ScopeId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class AdminUserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    account_status: AccountStatus
    full_name: str | None
    created_at: datetime
    last_login_at: datetime | None


class UserStatusUpdate(BaseModel):
    account_status: AccountStatus


class SpecialtyCreate(BaseModel):
    name: SpecialtyName
    description: LongText | None = None


class SpecialtyUpdate(BaseModel):
    name: SpecialtyName | None = None
    description: LongText | None = None
    is_active: bool | None = None


class HospitalCreate(BaseModel):
    name: Name
    facility_type: FacilityType = FacilityType.HOSPITAL
    address: Address
    city: City
    phone: FacilityPhone | None = None
    email: EmailStr | None = None
    website: WebUrl | None = None
    avatar_url: Url | None = None
    description: LongText | None = None


class HospitalUpdate(BaseModel):
    name: Name | None = None
    facility_type: FacilityType | None = None
    address: Address | None = None
    city: City | None = None
    phone: FacilityPhone | None = None
    email: EmailStr | None = None
    website: WebUrl | None = None
    avatar_url: Url | None = None
    description: LongText | None = None
    is_active: bool | None = None


class DepartmentCreate(BaseModel):
    hospital_id: int
    specialty_id: int
    name: DepartmentName
    description: LongText | None = None
    location: ShortText | None = None
    visibility: DepartmentVisibility = DepartmentVisibility.PUBLIC


class DepartmentUpdate(BaseModel):
    specialty_id: int | None = None
    name: DepartmentName | None = None
    description: LongText | None = None
    location: ShortText | None = None
    visibility: DepartmentVisibility | None = None
    is_active: bool | None = None


class DepartmentAdminOut(DepartmentOut):
    visibility: DepartmentVisibility


class DoctorCreate(BaseModel):
    # The doctor's facility and specialty are those of its department.
    department_id: int
    full_name: DoctorName
    title: DoctorTitle | None = None
    qualifications: LongText | None = None
    experience_years: int = Field(default=0, ge=0, le=70)
    introduction: LongText | None = None
    avatar_url: Url | None = None
    erp_doctor_id: ErpDoctorId | None = None
    max_appointments_per_window: Capacity = 1
    scheduling_mode: SchedulingMode = SchedulingMode.ERP


class DoctorUpdate(BaseModel):
    department_id: int | None = None
    full_name: DoctorName | None = None
    title: DoctorTitle | None = None
    qualifications: LongText | None = None
    experience_years: int | None = Field(default=None, ge=0, le=70)
    introduction: LongText | None = None
    avatar_url: Url | None = None
    erp_doctor_id: ErpDoctorId | None = None
    is_active: bool | None = None
    max_appointments_per_window: Capacity | None = None
    scheduling_mode: SchedulingMode | None = None

    @field_validator("max_appointments_per_window", "scheduling_mode", mode="before")
    @classmethod
    def capacity_cannot_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Scheduling settings cannot be empty.")
        return value


class AdminDoctorDetail(DoctorDetail):
    max_appointments_per_window: int
    scheduling_mode: SchedulingMode


class AppointmentTypeCreate(BaseModel):
    name: Name
    description: LongText | None = None
    duration_minutes: Duration
    buffer_minutes: Buffer = 0
    fee_override: Decimal | None = Field(default=None, ge=0)
    specialty_id: ScopeId | None = None
    doctor_id: ScopeId | None = None


class AppointmentTypeUpdate(BaseModel):
    name: Name | None = None
    description: LongText | None = None
    duration_minutes: Duration | None = None
    buffer_minutes: Buffer | None = None
    fee_override: Decimal | None = Field(default=None, ge=0)
    specialty_id: ScopeId | None = None
    doctor_id: ScopeId | None = None
    is_active: bool | None = None

    @field_validator("duration_minutes", "buffer_minutes", mode="before")
    @classmethod
    def timing_cannot_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Duration and buffer cannot be empty.")
        return value


class AppointmentTypeAdminOut(AppointmentTypeOut):
    fee_override: Decimal | None
    specialty_id: int | None
    doctor_id: int | None


class PaymentStatusSummary(BaseModel):
    status: PaymentStatus
    count: int
    total_amount: Decimal


class SpecialtyStat(BaseModel):
    specialty_id: int
    name: str
    count: int


class ReportSummary(BaseModel):
    appointments_by_status: dict[str, int]
    payments_by_status: list[PaymentStatusSummary]
    top_specialties: list[SpecialtyStat]
    total_patients: int
    generated_at: datetime


class AuditLogOut(ORMModel):
    id: int
    actor_id: int | None
    actor_type: ActorType
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any] | None
    request_id: str | None
    created_at: datetime


class ScheduleSyncResult(BaseModel):
    doctors_synced: int
    success: bool
