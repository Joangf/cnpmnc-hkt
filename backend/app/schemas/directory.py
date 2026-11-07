import datetime as dt
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import FacilityType
from app.schemas.common import ORMModel, RefOut


class SpecialtyOut(ORMModel):
    id: int
    name: str
    description: str | None
    is_active: bool


class DepartmentOut(BaseModel):
    id: int
    hospital_id: int
    name: str
    description: str | None
    specialty: SpecialtyOut
    is_active: bool


class HospitalSummary(BaseModel):
    id: int
    name: str
    facility_type: FacilityType
    address: str
    city: str
    phone: str | None
    email: str | None
    avatar_url: str | None
    description: str | None
    is_active: bool
    specialties: list[SpecialtyOut]


class HospitalDetail(HospitalSummary):
    website: str | None
    departments: list[DepartmentOut]


class DoctorSummary(BaseModel):
    id: int
    full_name: str
    title: str | None
    experience_years: int
    consultation_fee: Decimal | None
    currency: str
    rating_avg: Decimal
    rating_count: int
    avatar_url: str | None
    hospital: RefOut
    department: RefOut
    specialty: RefOut
    is_active: bool


class DoctorDetail(DoctorSummary):
    qualifications: str | None
    introduction: str | None
    erp_doctor_id: str | None


class AppointmentTypeOut(BaseModel):
    id: int
    name: str
    description: str | None
    duration_minutes: int
    buffer_minutes: int
    fee: Decimal | None
    currency: str
    is_active: bool


class SlotOut(BaseModel):
    start_time: dt.datetime
    end_time: dt.datetime


class AvailabilityResponse(BaseModel):
    doctor_id: int
    date: dt.date
    appointment_type_id: int
    timezone: str
    slots: list[SlotOut]
    generated_at: dt.datetime
    # Displayed availability is not a guarantee (FRD 4.4.2); it is revalidated on booking.
    source: str
