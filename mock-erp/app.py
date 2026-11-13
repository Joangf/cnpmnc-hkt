"""Mock hospital ERP/HIS - SIMULATED, not a real integration (FRD 3.3 assumption 3/4).

Provides doctor schedules, accepts bookings (with its own overlap check, as an
authoritative system would) and pushes signed status webhooks to the platform.
State is persisted in SQLite across restarts. Use /docs to drive simulations manually:

    POST /simulate/bookings/{ref}/status    {"status": "COMPLETED"}
    POST /simulate/bookings/{ref}/check-in
    POST /simulate/bookings/{ref}/reschedule {"start_time": ..., "end_time": ...}
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime
from typing import Literal

import httpx
from catalog import occupied
from catalog import router as catalog_router
from fastapi import FastAPI, HTTPException, Query
from pydantic import AwareDatetime, BaseModel
from store import get, put, rows, transaction
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("CLINIC_TIMEZONE", "Asia/Ho_Chi_Minh"))
MODE = os.getenv(
    "MOCK_ERP_MODE", "sync"
)  # sync: confirm immediately | async: confirm via webhook
REJECT_RATE = float(os.getenv("MOCK_ERP_REJECT_RATE", "0"))
LATENCY_MS = int(os.getenv("MOCK_ERP_LATENCY_MS", "50"))
ASYNC_DELAY_SECONDS = float(os.getenv("MOCK_ERP_ASYNC_DELAY_SECONDS", "5"))
WEBHOOK_URL = os.getenv(
    "ERP_WEBHOOK_URL", "http://backend:8000/api/v1/integrations/erp/events"
)
WEBHOOK_SECRET = os.getenv("ERP_WEBHOOK_SECRET", "erp-webhook-secret")

WORKING_HOURS = [(dtime(8, 0), dtime(11, 30)), (dtime(13, 30), dtime(17, 0))]
ACTIVE = {"PENDING", "CONFIRMED"}

Status = Literal[
    "PENDING", "CONFIRMED", "REJECTED", "CANCELLED", "COMPLETED", "NO_SHOW"
]

app = FastAPI(title="Mock ERP/HIS (simulated)", version="0.2.0")
app.include_router(catalog_router)


class BookingIn(BaseModel):
    booking_reference: str
    erp_doctor_id: str
    start_time: AwareDatetime
    end_time: AwareDatetime
    patient_ref: str
    slot_id: str | None = None
    slot_version: int | None = None


class Booking(BaseModel):
    booking_reference: str
    erp_booking_id: str
    erp_doctor_id: str
    start_time: datetime
    end_time: datetime
    patient_ref: str
    slot_id: str | None = None
    slot_version: int | None = None
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


def _load(reference: str) -> Booking | None:
    with transaction() as db:
        body = get(db, "bookings", reference)
        return Booking.model_validate(body) if body else None


def _save(booking: Booking) -> None:
    with transaction() as db:
        put(db, "bookings", booking.booking_reference, booking.model_dump(mode="json"))


def _windows(erp_doctor_id: str, day: date) -> list[tuple[datetime, datetime]]:
    if day.weekday() == 6:  # Sunday closed
        return []
    hours = WORKING_HOURS
    # Variety: doctors with an odd number don't work Saturday afternoons.
    if (
        day.weekday() == 5
        and erp_doctor_id[-1:].isdigit()
        and int(erp_doctor_id[-1]) % 2
    ):
        hours = WORKING_HOURS[:1]
    return [
        (datetime.combine(day, a, tzinfo=TZ), datetime.combine(day, b, tzinfo=TZ))
        for a, b in hours
    ]


def _sign(body: bytes) -> tuple[str, str]:
    ts = str(int(time.time()))
    return ts, hmac.new(
        WEBHOOK_SECRET.encode(), ts.encode() + b"." + body, hashlib.sha256
    ).hexdigest()


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
    headers = {
        "content-type": "application/json",
        "x-erp-timestamp": ts,
        "x-erp-signature": signature,
    }
    async with httpx.AsyncClient(timeout=5) as client:
        for attempt in range(3):
            try:
                response = await client.post(WEBHOOK_URL, content=body, headers=headers)
                return {
                    "webhook_status": response.status_code,
                    "webhook_response": response.text[:500],
                }
            except httpx.HTTPError as exc:
                if attempt == 2:
                    return {"webhook_status": None, "webhook_error": str(exc)}
                await asyncio.sleep(1 + attempt)
    return {}


async def _confirm_later(reference: str) -> None:
    await asyncio.sleep(ASYNC_DELAY_SECONDS)
    async with _lock:
        booking = _load(reference)
        if booking is None or booking.status != "PENDING":
            return
        booking.status = "CONFIRMED"
        _save(booking)
    await _push("APPOINTMENT_STATUS_CHANGED", booking)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "mode": MODE}


@app.get("/doctors/{erp_doctor_id}/schedule")
async def get_schedule(
    erp_doctor_id: str, from_: date = Query(alias="from"), to: date = Query()
) -> list[dict]:
    if (to - from_).days > 60:
        raise HTTPException(422, "Range too large")
    result = []
    day = from_
    while day <= to:
        for start, end in _windows(erp_doctor_id, day):
            result.append(
                {
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "max_appointments": None,
                    "is_available": True,
                }
            )
        day += timedelta(days=1)
    return result


@app.post("/bookings", status_code=201)
async def create_booking(data: BookingIn) -> Booking:
    await asyncio.sleep(LATENCY_MS / 1000)
    with transaction() as db:
        existing = get(db, "bookings", data.booking_reference)
        if existing:
            if any(
                existing.get(k) != getattr(data, k)
                for k in ("erp_doctor_id", "patient_ref", "slot_id")
            ):
                raise HTTPException(409, "Booking reference already used")
            return Booking.model_validate(existing)
        slot = get(db, "slots", data.slot_id)
        doctor = get(db, "doctors", data.erp_doctor_id)
        valid = (
            slot
            and doctor
            and doctor["data"].get("is_active", True)
            and slot["doctor_id"] == data.erp_doctor_id
            and slot["is_open"]
            and slot["version"] == data.slot_version
            and datetime.fromisoformat(slot["start_time"]) == data.start_time
            and datetime.fromisoformat(slot["end_time"]) == data.end_time
            and data.start_time > datetime.now(UTC)
        )
        duplicate = any(
            b.get("slot_id") == data.slot_id
            and b["patient_ref"] == data.patient_ref
            and b["status"] in ACTIVE
            for b in rows(db, "bookings")
        )
        accepted = (
            valid and not duplicate and occupied(db, data.slot_id) < slot["capacity"]
        )
        booking = Booking(
            **data.model_dump(),
            erp_booking_id=f"ERP-{uuid.uuid4().hex[:10].upper()}",
            status=("CONFIRMED" if MODE == "sync" else "PENDING")
            if accepted
            else "REJECTED",
            reason=None
            if accepted
            else "Slot changed, closed, full, or already booked.",
        )
        put(db, "bookings", data.booking_reference, booking.model_dump(mode="json"))
    if booking.status == "PENDING":
        asyncio.create_task(_confirm_later(booking.booking_reference))
    return booking


@app.get("/bookings")
async def list_bookings(limit: int = 100) -> list[Booking]:
    with transaction() as db:
        return sorted(
            rows(db, "bookings"), key=lambda b: b["start_time"], reverse=True
        )[:limit]


@app.get("/bookings/{booking_reference}")
async def get_booking(booking_reference: str) -> Booking:
    booking = _load(booking_reference)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    return booking


@app.post("/bookings/by-id/{erp_booking_id}/cancel")
async def cancel_booking(erp_booking_id: str, data: CancelIn) -> Booking:
    with transaction() as db:
        body = next(
            (b for b in rows(db, "bookings") if b["erp_booking_id"] == erp_booking_id),
            None,
        )
        if body is None:
            return Booking(
                booking_reference=erp_booking_id,
                erp_booking_id=erp_booking_id,
                erp_doctor_id="DR-1",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC) + timedelta(minutes=30),
                patient_ref="P1",
                status="CANCELLED",
                reason=data.reason,
            )
        if body["status"] == "CANCELLED":
            return Booking.model_validate(body)
        if body["status"] not in ACTIVE or body["check_in_status"] == "CHECKED_IN":
            raise HTTPException(409, "Booking cannot be cancelled")
        body.update(status="CANCELLED", reason=data.reason)
        put(db, "bookings", body["booking_reference"], body)
    return Booking.model_validate(body)


# --- Simulation endpoints: what hospital staff would do in the real ERP/HIS ------------------


def _require(reference: str) -> Booking:
    booking = _load(reference)
    if booking is None:
        booking = Booking(
            booking_reference=reference,
            erp_booking_id=f"ERP-{uuid.uuid4().hex[:10].upper()}",
            erp_doctor_id="DR-1",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(minutes=30),
            patient_ref="P1",
            status="CONFIRMED",
        )
        _bookings[reference] = booking
    return booking


@app.post("/simulate/bookings/{booking_reference}/status", tags=["simulate"])
async def simulate_status(booking_reference: str, data: StatusIn) -> dict:
    booking = _require(booking_reference)
    allowed = {
        "PENDING": {"CONFIRMED", "REJECTED", "CANCELLED"},
        "CONFIRMED": {"COMPLETED", "NO_SHOW", "CANCELLED", "REJECTED"},
    }
    if data.status not in allowed.get(booking.status, set()):
        raise HTTPException(409, "Invalid status transition")
    booking.status, booking.reason = data.status, data.reason
    _save(booking)
    return {"booking": booking, **(await _push("APPOINTMENT_STATUS_CHANGED", booking))}


@app.post("/simulate/bookings/{booking_reference}/check-in", tags=["simulate"])
async def simulate_check_in(booking_reference: str) -> dict:
    booking = _require(booking_reference)
    if booking.status != "CONFIRMED":
        raise HTTPException(409, "Only confirmed appointments can check in")
    booking.check_in_status = "CHECKED_IN"
    _save(booking)
    return {"booking": booking, **(await _push("CHECK_IN_STATUS_CHANGED", booking))}


@app.post("/simulate/bookings/{booking_reference}/reschedule", tags=["simulate"])
async def simulate_reschedule(booking_reference: str, data: RescheduleIn) -> dict:
    booking = _require(booking_reference)
    if booking.slot_id:
        raise HTTPException(
            409,
            "Shared-slot bookings must be cancelled and booked again to change time",
        )
    booking.start_time, booking.end_time, booking.reason = (
        data.start_time,
        data.end_time,
        data.reason,
    )
    _save(booking)
    result = await _push(
        "APPOINTMENT_RESCHEDULED",
        booking,
        start_time=data.start_time.isoformat(),
        end_time=data.end_time.isoformat(),
    )
    return {"booking": booking, **result}
