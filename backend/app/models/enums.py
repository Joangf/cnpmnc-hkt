"""Status enums (FRD section 7). Stored as strings; names equal values."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class UserRole(StrEnum):
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FacilityType(StrEnum):
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"


class DepartmentVisibility(StrEnum):
    """Whether a department/clinic is published in the public directory.

    DISABLED is represented by Department.is_active = False; the two are checked
    together so unpublished, hidden and inactive departments never leak publicly.
    """

    PUBLIC = "PUBLIC"
    UNPUBLISHED = "UNPUBLISHED"
    HIDDEN = "HIDDEN"


class AppointmentStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


# Statuses that hold a slot. Must match the WHERE clause of the `no_overlap` constraint.
ACTIVE_APPOINTMENT_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)


class CheckInStatus(StrEnum):
    NOT_CHECKED_IN = "NOT_CHECKED_IN"
    CHECKED_IN = "CHECKED_IN"
    UNKNOWN = "UNKNOWN"


class PaymentStatus(StrEnum):
    UNPAID = "UNPAID"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"
    REMOVED = "REMOVED"


class StatusSource(StrEnum):
    PLATFORM = "PLATFORM"
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"
    ERP = "ERP"
    SYSTEM = "SYSTEM"


class ActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    ERP = "ERP"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY"


class NotificationType(StrEnum):
    BOOKING_SUBMITTED = "BOOKING_SUBMITTED"
    APPOINTMENT_STATUS = "APPOINTMENT_STATUS"
    CHECK_IN = "CHECK_IN"
    PAYMENT_RESULT = "PAYMENT_RESULT"
    ACCOUNT = "ACCOUNT"


class ScheduleSource(StrEnum):
    ERP = "ERP"
    LOCAL = "LOCAL"


def enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
