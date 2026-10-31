from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field

from app.models.enums import AppointmentStatus, CheckInStatus, PaymentStatus, StatusSource
from app.schemas.common import ORMModel, RefOut
from app.schemas.validators import ShortText


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    appointment_type_id: int = Field(gt=0)
    start_time: AwareDatetime
    reason_for_visit: ShortText | None = None


class CancelRequest(BaseModel):
    reason: ShortText | None = None


class StatusHistoryOut(ORMModel):
    field: str
    from_value: str | None
    to_value: str
    reason: str | None
    source: StatusSource
    created_at: datetime


class PaymentSummary(ORMModel):
    id: int
    status: PaymentStatus
    amount: Decimal
    currency: str
    provider_reference: str | None
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime


class AppointmentSummary(BaseModel):
    id: int
    booking_reference: str
    status: AppointmentStatus
    status_reason: str | None
    check_in_status: CheckInStatus
    payment_status: PaymentStatus
    start_time: datetime
    end_time: datetime
    doctor: RefOut
    hospital: RefOut
    department: RefOut
    appointment_type: RefOut
    fee_amount: Decimal
    currency: str


class AppointmentDetail(AppointmentSummary):
    reason_for_visit: str | None
    history: list[StatusHistoryOut]
    payments: list[PaymentSummary]
    can_cancel: bool
    can_pay: bool
    can_review: bool
    has_review: bool
    cancellation_deadline: datetime


class AdminAppointmentOut(AppointmentSummary):
    patient_id: int
