"""Mock hospital ERP/HIS - SIMULATED, not a real integration (FRD 3.3 assumption 3/4).

Provides doctor schedules, accepts bookings (with its own overlap check, as an
authoritative system would) and pushes signed status webhooks to the platform.
State is in memory and resets on restart. Use /docs to drive simulations manually:

    POST /simulate/bookings/{ref}/status    {"status": "COMPLETED"}
    POST /simulate/bookings/{ref}/check-in
    POST /simulate/bookings/{ref}/reschedule {"start_time": ..., "end_time": ...}
"""

import asyncio
import hashlib
import hmac
import json
import os
import random
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import AwareDatetime, BaseModel

TZ = ZoneInfo(os.getenv("CLINIC_TIMEZONE", "Asia/Ho_Chi_Minh"))
MODE = os.getenv("MOCK_ERP_MODE", "sync")  # sync: confirm immediately | async: confirm via webhook
REJECT_RATE = float(os.getenv("MOCK_ERP_REJECT_RATE", "0"))
LATENCY_MS = int(os.getenv("MOCK_ERP_LATENCY_MS", "50"))
ASYNC_DELAY_SECONDS = float(os.getenv("MOCK_ERP_ASYNC_DELAY_SECONDS", "5"))
WEBHOOK_URL = os.getenv("ERP_WEBHOOK_URL", "http://backend:8000/api/v1/integrations/erp/events")
WEBHOOK_SECRET = os.getenv("ERP_WEBHOOK_SECRET", "erp-webhook-secret")

WORKING_HOURS = [(dtime(8, 0), dtime(11, 30)), (dtime(13, 30), dtime(17, 0))]
ACTIVE = {"PENDING", "CONFIRMED"}

Status = Literal["PENDING", "CONFIRMED", "REJECTED", "CANCELLED", "COMPLETED", "NO_SHOW"]

app = FastAPI(title="Mock ERP/HIS (simulated)", version="0.1.0")


class BookingIn(BaseModel):
    booking_reference: str
    erp_doctor_id: str
    start_time: AwareDatetime
    end_time: AwareDatetime
    patient_ref: str


class Booking(BaseModel):
    booking_reference: str
    erp_booking_id: str
    erp_doctor_id: str
    start_time: datetime
    end_time: datetime
    patient_ref: str
    status: Status
    check_in_status: Literal["NOT_CHECKED_IN", "CHECKED_IN"] = "NOT_CHECKED_IN"
    reason: str | None = None


class CancelIn(BaseModel):
    reason: str | None = None


class StatusIn(BaseModel):
    status: Status
    reason: str | None = None


class RescheduleIn(BaseModel):
    start_time: AwareDatetime
    end_time: AwareDatetime
    reason: str | None = "Rescheduled by the hospital"


_lock = asyncio.Lock()
_bookings: dict[str, Booking] = {}  # by booking_reference


def _windows(erp_doctor_id: str, day: date) -> list[tuple[datetime, datetime]]:
    if day.weekday() == 6:  # Sunday closed
        return []
    hours = WORKING_HOURS
    # Variety: doctors with an odd number don't work Saturday afternoons.
    if day.weekday() == 5 and erp_doctor_id[-1:].isdigit() and int(erp_doctor_id[-1]) % 2:
        hours = WORKING_HOURS[:1]
    return [(datetime.combine(day, a, tzinfo=TZ), datetime.combine(day, b, tzinfo=TZ)) for a, b in hours]


def _sign(body: bytes) -> tuple[str, str]:
    ts = str(int(time.time()))
    return ts, hmac.new(WEBHOOK_SECRET.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()


async def _push(event_type: str, booking: Booking, **extra: object) -> dict:
    payload = {
        "event_id": uuid.uuid4().hex,
        "type": event_type,
        "booking_reference": booking.booking_reference,
        "erp_booking_id": booking.erp_booking_id,
        "status": booking.status,
        "check_in_status": booking.check_in_status,
        "reason": booking.reason,
        "occurred_at": datetime.now(UTC).isoformat(),
        **extra,
    }
    body = json.dumps(payload).encode()
    ts, signature = _sign(body)
    headers = {"content-type": "application/json", "x-erp-timestamp": ts, "x-erp-signature": signature}
    async with httpx.AsyncClient(timeout=5) as client:
        for attempt in range(3):
            try:
                response = await client.post(WEBHOOK_URL, content=body, headers=headers)
                return {"webhook_status": response.status_code, "webhook_response": response.text[:500]}
            except httpx.HTTPError as exc:
                if attempt == 2:
                    return {"webhook_status": None, "webhook_error": str(exc)}
                await asyncio.sleep(1 + attempt)
    return {}


async def _confirm_later(reference: str) -> None:
    await asyncio.sleep(ASYNC_DELAY_SECONDS)
    async with _lock:
        booking = _bookings.get(reference)
        if booking is None or booking.status != "PENDING":
            return
        booking.status = "CONFIRMED"
    await _push("APPOINTMENT_STATUS_CHANGED", booking)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode": MODE}


@app.get("/doctors/{erp_doctor_id}/schedule")
async def get_schedule(erp_doctor_id: str, from_: date = Query(alias="from"), to: date = Query()) -> list[dict]:
    if (to - from_).days > 60:
        raise HTTPException(422, "Range too large")
    result = []
    day = from_
    while day <= to:
        for start, end in _windows(erp_doctor_id, day):
            result.append({"start_time": start.isoformat(), "end_time": end.isoformat(),
                           "max_appointments": None, "is_available": True})
        day += timedelta(days=1)
    return result


@app.post("/bookings", status_code=201)
async def create_booking(data: BookingIn) -> Booking:
    await asyncio.sleep(LATENCY_MS / 1000)
    async with _lock:
        if data.booking_reference in _bookings:  # idempotent on the platform's reference
            return _bookings[data.booking_reference]

        booking = Booking(
            booking_reference=data.booking_reference,
            erp_booking_id=f"ERP-{uuid.uuid4().hex[:10].upper()}",
            erp_doctor_id=data.erp_doctor_id,
            start_time=data.start_time,
            end_time=data.end_time,
            patient_ref=data.patient_ref,
            status="PENDING",
        )
        local_day = data.start_time.astimezone(TZ).date()
        within_hours = any(s <= data.start_time and data.end_time <= e for s, e in _windows(data.erp_doctor_id, local_day))
        overlaps = any(
            b.erp_doctor_id == data.erp_doctor_id and b.status in ACTIVE
            and b.start_time < data.end_time and data.start_time < b.end_time
            for b in _bookings.values()
        )
        if not within_hours:
            booking.status, booking.reason = "REJECTED", "Outside the doctor's working hours."
        elif overlaps:
            booking.status, booking.reason = "REJECTED", "This time is no longer available at the hospital."
        elif random.random() < REJECT_RATE:
            booking.status, booking.reason = "REJECTED", "The hospital could not accept this booking."
        elif MODE == "sync":
            booking.status = "CONFIRMED"
        _bookings[booking.booking_reference] = booking

    if booking.status == "PENDING":
        asyncio.create_task(_confirm_later(booking.booking_reference))
    return booking


@app.get("/bookings")
async def list_bookings(limit: int = 100) -> list[Booking]:
    return sorted(_bookings.values(), key=lambda b: b.start_time, reverse=True)[:limit]


@app.get("/bookings/{booking_reference}")
async def get_booking(booking_reference: str) -> Booking:
    booking = _bookings.get(booking_reference)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    return booking


@app.post("/bookings/by-id/{erp_booking_id}/cancel")
async def cancel_booking(erp_booking_id: str, data: CancelIn) -> Booking:
    async with _lock:
        booking = next((b for b in _bookings.values() if b.erp_booking_id == erp_booking_id), None)
        if booking is None:
            raise HTTPException(404, "Booking not found")
        if booking.status not in ACTIVE:
            raise HTTPException(409, f"Booking is {booking.status} and can no longer be cancelled")
        booking.status, booking.reason = "CANCELLED", data.reason
    return booking


# --- Simulation endpoints: what hospital staff would do in the real ERP/HIS ------------------


def _require(reference: str) -> Booking:
    booking = _bookings.get(reference)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    return booking


@app.post("/simulate/bookings/{booking_reference}/status", tags=["simulate"])
async def simulate_status(booking_reference: str, data: StatusIn) -> dict:
    booking = _require(booking_reference)
    booking.status, booking.reason = data.status, data.reason
    return {"booking": booking, **(await _push("APPOINTMENT_STATUS_CHANGED", booking))}


@app.post("/simulate/bookings/{booking_reference}/check-in", tags=["simulate"])
async def simulate_check_in(booking_reference: str) -> dict:
    booking = _require(booking_reference)
    booking.check_in_status = "CHECKED_IN"
    return {"booking": booking, **(await _push("CHECK_IN_STATUS_CHANGED", booking))}


@app.post("/simulate/bookings/{booking_reference}/reschedule", tags=["simulate"])
async def simulate_reschedule(booking_reference: str, data: RescheduleIn) -> dict:
    booking = _require(booking_reference)
    booking.start_time, booking.end_time, booking.reason = data.start_time, data.end_time, data.reason
    result = await _push(
        "APPOINTMENT_RESCHEDULED", booking,
        start_time=data.start_time.isoformat(), end_time=data.end_time.isoformat(),
    )
    return {"booking": booking, **result}
