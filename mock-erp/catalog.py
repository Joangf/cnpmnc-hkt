"""Swagger endpoints for the simulated hospital's directory and shared slots."""

from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from store import KINDS, get, put, rows, transaction

router = APIRouter()
Kind = Literal[
    "hospitals", "specialties", "departments", "doctors", "appointment_types"
]


class Entity(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    data: dict


class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    doctor_id: str
    start_time: AwareDatetime
    end_time: AwareDatetime
    capacity: int = Field(default=1, gt=0, strict=True)
    is_open: bool = True
    version: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def timing(self):
        if (
            not timedelta(minutes=5)
            <= self.end_time - self.start_time
            <= timedelta(hours=8)
        ):
            raise ValueError("Slot duration must be 5–480 minutes")
        if any(t.second or t.microsecond for t in (self.start_time, self.end_time)):
            raise ValueError("Use whole minutes")
        zone = ZoneInfo(os.getenv("CLINIC_TIMEZONE", "Asia/Ho_Chi_Minh"))
        if self.start_time.astimezone(zone).date() != self.end_time.astimezone(zone).date():
            raise ValueError("Slot must fit within one clinic date")
        return self


def occupied(db, slot_id):
    return sum(
        b.get("slot_id") == slot_id and b["status"] in ("PENDING", "CONFIRMED")
        for b in rows(db, "bookings")
    )


@router.get("/catalog", tags=["directory"])
def catalog():
    with transaction() as db:
        result = {kind: rows(db, kind) for kind in KINDS if kind != "bookings"}
        for s in result["slots"]:
            s["booked_count"] = occupied(db, s["id"])
        return result


@router.put("/directory/{kind}/{identifier}", tags=["directory"])
def save_entity(kind: Kind, identifier: str, entity: Entity):
    if identifier != entity.id:
        raise HTTPException(422, "IDs must match")
    with transaction() as db:
        put(db, kind, identifier, entity.model_dump(mode="json"))
    return entity


@router.put("/slots/{identifier}", tags=["slots"])
def save_slot(identifier: str, slot: Slot):
    if identifier != slot.id:
        raise HTTPException(422, "IDs must match")
    with transaction() as db:
        if not get(db, "doctors", slot.doctor_id):
            raise HTTPException(422, "Unknown doctor")
        previous = get(db, "slots", identifier)
        if previous:
            if slot.version != previous["version"]:
                raise HTTPException(409, "Slot changed; reload the catalog")
            if occupied(db, identifier) and any(
                (datetime.fromisoformat(previous[k]) != getattr(slot, k))
                if k in ("start_time", "end_time") else previous[k] != getattr(slot, k)
                for k in ("doctor_id", "start_time", "end_time")
            ):
                raise HTTPException(409, "Booked slot times are locked")
        for other in rows(db, "slots"):
            if other["id"] == identifier or other["doctor_id"] != slot.doctor_id:
                continue
            if slot.start_time < datetime.fromisoformat(other["end_time"]) and datetime.fromisoformat(
                other["start_time"]
            ) < slot.end_time:
                raise HTTPException(409, "Slots cannot overlap")
        body = slot.model_dump(mode="json")
        body["version"] = previous["version"] + 1 if previous else 1
        put(db, "slots", identifier, body)
        return body


class Bootstrap(BaseModel):
    catalog: dict[str, list[dict]]
    bookings: list[dict]


@router.post("/simulate/bootstrap", tags=["migration"])
def bootstrap(payload: Bootstrap):
    """One-time import into an empty mock ERP; exact retries are safe, conflicts abort."""
    with transaction() as db:
        for kind, values in {**payload.catalog, "bookings": payload.bookings}.items():
            if kind not in KINDS:
                raise HTTPException(422, "Unknown entity kind")
            for value in values:
                identifier = (
                    value["booking_reference"] if kind == "bookings" else value["id"]
                )
                old = get(db, kind, identifier)
                if old and old != value:
                    raise HTTPException(
                        409, f"Existing ERP data differs: {kind}/{identifier}"
                    )
                put(db, kind, identifier, value)
    return {"imported": True}
