"""Pure business-rule helpers shared by services and presenters."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.models import Appointment, AppointmentType, Doctor, Payment
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus, PaymentStatus


def effective_fee(doctor: Doctor, appointment_type: AppointmentType) -> Decimal:
    return appointment_type.fee_override or Decimal("0")


def doctor_is_published(doctor: Doctor) -> bool:
    """A doctor is public and bookable only while it and every record it links to
    (department, specialty, facility) are active. Mirrors `directory._published_doctor()`.
    Requires `doctor.hospital` and `doctor.department.specialty` to be loaded."""
    department = doctor.department
    return (
        doctor.is_active
        and doctor.hospital.is_active
        and department.is_active
        and department.specialty.is_active
    )


def type_applies_to_doctor(appointment_type: AppointmentType, doctor: Doctor) -> bool:
    """Requires `doctor.department` to be loaded."""
    if not appointment_type.is_active:
        return False
    if appointment_type.doctor_id is not None:
        return appointment_type.doctor_id == doctor.id and (
            appointment_type.specialty_id is None
            or appointment_type.specialty_id == doctor.department.specialty_id
        )
    if appointment_type.specialty_id is not None:
        return appointment_type.specialty_id == doctor.department.specialty_id
    return True


def cancellation_deadline(start_time: datetime) -> datetime:
    return start_time - timedelta(hours=settings.cancellation_cutoff_hours)


def can_cancel(appointment: Appointment, now: datetime | None = None) -> bool:
    """BR-06: active appointments, up to the configured cut-off before start."""
    now = now or datetime.now(UTC)
    return appointment.status in ACTIVE_APPOINTMENT_STATUSES and now <= cancellation_deadline(
        appointment.start_time
    )


def payment_status_of(payments: Sequence[Payment]) -> PaymentStatus:
    """Appointment-level payment status derived from its attempts (BR-07)."""
    if not payments:
        return PaymentStatus.UNPAID
    for payment in reversed(payments):
        if payment.status in (PaymentStatus.PAID, PaymentStatus.REFUNDED):
            return payment.status
    return payments[-1].status


def payment_allowed_for_status(status: AppointmentStatus) -> bool:
    # OQ-03: whether payment happens before or after hospital confirmation is configurable.
    if settings.payment_requires_confirmation:
        return status == AppointmentStatus.CONFIRMED
    return status in ACTIVE_APPOINTMENT_STATUSES


def can_pay(appointment: Appointment) -> bool:
    return (
        appointment.fee_amount > 0
        and payment_allowed_for_status(appointment.status)
        and payment_status_of(appointment.payments)
        in (PaymentStatus.UNPAID, PaymentStatus.FAILED, PaymentStatus.PENDING)
    )


def can_review(appointment: Appointment) -> bool:
    """BR-08 / BR-09. Requires `appointment.review` to be loaded."""
    return appointment.status == AppointmentStatus.COMPLETED and appointment.review is None
