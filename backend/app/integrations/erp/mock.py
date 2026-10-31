"""In-process ERP fake for tests and running without the mock-erp container (ERP_ADAPTER=memory)."""

import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.integrations.erp.base import (
    ErpAdapter,
    ErpBookingRequest,
    ErpBookingResult,
    ErpRejectedError,
    ErpScheduleWindow,
)

WORKING_HOURS = ((time(8, 0), time(11, 30)), (time(13, 30), time(17, 0)))


class InMemoryErpAdapter(ErpAdapter):
    name = "memory"

    def __init__(self) -> None:
        self._bookings: dict[str, ErpBookingResult] = {}

    async def get_schedule(
        self, erp_doctor_id: str, start: date, end: date
    ) -> list[ErpScheduleWindow]:
        tz = ZoneInfo(settings.clinic_timezone)
        windows = []
        day = start
        while day <= end:
            if day.weekday() < 6:  # Mon-Sat
                for open_at, close_at in WORKING_HOURS:
                    windows.append(
                        ErpScheduleWindow(
                            start_time=datetime.combine(day, open_at, tzinfo=tz),
                            end_time=datetime.combine(day, close_at, tzinfo=tz),
                        )
                    )
            day += timedelta(days=1)
        return windows

    async def create_booking(self, request: ErpBookingRequest) -> ErpBookingResult:
        existing = self._bookings.get(request.booking_reference)
        if existing:
            return existing
        result = ErpBookingResult(
            booking_reference=request.booking_reference,
            erp_booking_id=f"ERP-{uuid.uuid4().hex[:10].upper()}",
            status="CONFIRMED",
            check_in_status="NOT_CHECKED_IN",
        )
        self._bookings[request.booking_reference] = result
        return result

    async def get_booking(self, booking_reference: str) -> ErpBookingResult | None:
        return self._bookings.get(booking_reference)

    async def cancel_booking(self, erp_booking_id: str, reason: str | None) -> None:
        for ref, booking in self._bookings.items():
            if booking.erp_booking_id == erp_booking_id:
                if booking.status not in ("PENDING", "CONFIRMED"):
                    raise ErpRejectedError("Booking can no longer be cancelled.")
                self._bookings[ref] = ErpBookingResult(
                    booking_reference=ref,
                    erp_booking_id=erp_booking_id,
                    status="CANCELLED",
                    reason=reason,
                )
                return
        raise ErpRejectedError("Unknown booking.")
