"""HTTP ERP adapter. Talks to the `mock-erp` service today; point ERP_BASE_URL at a real
hospital API that implements the same contract (or adapt the mapping here)."""

import time
from datetime import date, datetime
from typing import Any

import httpx

from app.core.metrics import ERP_CALLS
from app.integrations.erp.base import (
    ErpAdapter,
    ErpBookingRequest,
    ErpBookingResult,
    ErpRejectedError,
    ErpScheduleWindow,
    ErpTimeoutError,
    ErpUnavailableError,
)


def _result(data: dict[str, Any]) -> ErpBookingResult:
    return ErpBookingResult(
        booking_reference=data["booking_reference"],
        erp_booking_id=data.get("erp_booking_id"),
        status=data["status"],
        reason=data.get("reason"),
        check_in_status=data.get("check_in_status"),
    )


class HttpErpAdapter(ErpAdapter):
    name = "http"

    def __init__(self, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def _request(
        self, operation: str, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        start = time.perf_counter()
        outcome = "ok"
        try:
            response = await self._client.request(method, url, **kwargs)
            if response.status_code >= 500:
                outcome = "error"
                raise ErpUnavailableError(f"ERP returned HTTP {response.status_code}")
            return response
        except httpx.ConnectTimeout as exc:
            outcome = "error"
            raise ErpUnavailableError("ERP connection timed out") from exc
        except httpx.TimeoutException as exc:
            outcome = "timeout"
            raise ErpTimeoutError("ERP did not respond in time") from exc
        except httpx.HTTPError as exc:
            outcome = "error"
            raise ErpUnavailableError(str(exc)) from exc
        finally:
            ERP_CALLS.labels(operation=operation, outcome=outcome).observe(
                time.perf_counter() - start
            )

    async def get_schedule(
        self, erp_doctor_id: str, start: date, end: date
    ) -> list[ErpScheduleWindow]:
        response = await self._request(
            "get_schedule",
            "GET",
            f"/doctors/{erp_doctor_id}/schedule",
            params={"from": start.isoformat(), "to": end.isoformat()},
        )
        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise ErpUnavailableError(f"Unexpected ERP response {response.status_code}")
        return [
            ErpScheduleWindow(
                start_time=datetime.fromisoformat(item["start_time"]),
                end_time=datetime.fromisoformat(item["end_time"]),
                max_appointments=item.get("max_appointments"),
                is_available=item.get("is_available", True),
            )
            for item in response.json()
        ]

    async def create_booking(self, request: ErpBookingRequest) -> ErpBookingResult:
        response = await self._request(
            "create_booking",
            "POST",
            "/bookings",
            json={
                "booking_reference": request.booking_reference,
                "erp_doctor_id": request.erp_doctor_id,
                "start_time": request.start_time.isoformat(),
                "end_time": request.end_time.isoformat(),
                "patient_ref": request.patient_ref,
            },
        )
        if response.status_code not in (200, 201):
            raise ErpUnavailableError(f"Unexpected ERP response {response.status_code}")
        return _result(response.json())

    async def get_booking(self, booking_reference: str) -> ErpBookingResult | None:
        response = await self._request("get_booking", "GET", f"/bookings/{booking_reference}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ErpUnavailableError(f"Unexpected ERP response {response.status_code}")
        return _result(response.json())

    async def cancel_booking(self, erp_booking_id: str, reason: str | None) -> None:
        response = await self._request(
            "cancel_booking",
            "POST",
            f"/bookings/by-id/{erp_booking_id}/cancel",
            json={"reason": reason},
        )
        if response.status_code in (404, 409):
            detail = response.json().get("detail", "The hospital system refused the cancellation.")
            raise ErpRejectedError(str(detail))
        if response.status_code != 200:
            raise ErpUnavailableError(f"Unexpected ERP response {response.status_code}")

    async def aclose(self) -> None:
        await self._client.aclose()
