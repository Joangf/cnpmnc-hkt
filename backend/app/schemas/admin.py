from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AccountStatus, ActorType, FacilityType, PaymentStatus, UserRole
from app.schemas.common import ORMModel
from app.schemas.directory import AppointmentTypeOut
from app.schemas.validators import LongText, Name, bounded

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


class DepartmentUpdate(BaseModel):
    specialty_id: int | None = None
    name: DepartmentName | None = None
    description: LongText | None = None
    is_active: bool | None = None


class DoctorCreate(BaseModel):
    # The doctor's facility and specialty are those of its department.
    department_id: int
    full_name: DoctorName
    title: DoctorTitle | None = None
    qualifications: LongText | None = None
    experience_years: int = Field(default=0, ge=0, le=70)
    introduction: LongText | None = None
    consultation_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    avatar_url: Url | None = None
    erp_doctor_id: ErpDoctorId | None = None


class DoctorUpdate(BaseModel):
    department_id: int | None = None
    full_name: DoctorName | None = None
    title: DoctorTitle | None = None
    qualifications: LongText | None = None
    experience_years: int | None = Field(default=None, ge=0, le=70)
    introduction: LongText | None = None
    consultation_fee: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    avatar_url: Url | None = None
    erp_doctor_id: ErpDoctorId | None = None
    is_active: bool | None = None


class AppointmentTypeCreate(BaseModel):
    name: Name
    description: LongText | None = None
    duration_minutes: int = Field(ge=5, le=480)
    buffer_minutes: int = Field(default=0, ge=0, le=120)
    fee_override: Decimal | None = Field(default=None, ge=0)
    specialty_id: int | None = None
    doctor_id: int | None = None


class AppointmentTypeUpdate(BaseModel):
    name: Name | None = None
    description: LongText | None = None
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    buffer_minutes: int | None = Field(default=None, ge=0, le=120)
    fee_override: Decimal | None = Field(default=None, ge=0)
    specialty_id: int | None = None
    doctor_id: int | None = None
    is_active: bool | None = None


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
