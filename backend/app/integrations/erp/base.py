"""ERP/HIS adapter contract. The ERP is the source of truth for schedules, confirmation and
check-in (FRD 3.3). Status strings use the platform vocabulary (FRD section 7)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class ErpScheduleWindow:
    start_time: datetime
    end_time: datetime
    max_appointments: int | None = None
    is_available: bool = True


@dataclass(frozen=True, slots=True)
class ErpBookingRequest:
    booking_reference: str
    erp_doctor_id: str
    start_time: datetime
    end_time: datetime
    patient_ref: str  # opaque patient identifier; no PII is sent to the ERP mock


@dataclass(frozen=True, slots=True)
class ErpBookingResult:
    booking_reference: str
    erp_booking_id: str | None
    status: str  # PENDING | CONFIRMED | REJECTED | CANCELLED | COMPLETED | NO_SHOW
    reason: str | None = None
    check_in_status: str | None = None


class ErpError(Exception):
    """Base class for ERP integration failures."""


class ErpUnavailableError(ErpError):
    """The ERP could not be reached or failed; the request was not processed."""


class ErpTimeoutError(ErpError):
    """The ERP did not answer in time; the request may or may not have been processed."""


class ErpRejectedError(ErpError):
    """The ERP refused the operation (e.g. cancelling a completed booking)."""


class ErpAdapter(ABC):
    name: str

    @abstractmethod
    async def get_schedule(
        self, erp_doctor_id: str, start: date, end: date
    ) -> list[ErpScheduleWindow]: ...

    @abstractmethod
    async def create_booking(self, request: ErpBookingRequest) -> ErpBookingResult: ...

    @abstractmethod
    async def get_booking(self, booking_reference: str) -> ErpBookingResult | None: ...

    @abstractmethod
    async def cancel_booking(self, erp_booking_id: str, reason: str | None) -> None: ...

    async def aclose(self) -> None:
        return None
