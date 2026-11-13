"""python -m app.commands.erp_cutover [--apply]. Stop backend workers during --apply."""

import argparse
import asyncio
from datetime import datetime
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.integrations.erp.http import HttpErpAdapter
from app.models import Appointment, DoctorSlot, ErpSyncState
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES
from app.services.erp_catalog import MODELS, REFS, sync_catalog

EXCLUDE = {
    "id",
    "erp_id",
    "synced_at",
    "created_at",
    "updated_at",
    "rating_avg",
    "rating_count",
    "erp_doctor_id",
    "scheduling_mode",
    "buffer_minutes",
    "end_with_buffer",
    "erp_booked_count",
}


def serialize(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


async def run(apply=False):
    async with SessionLocal() as session:
        state = await session.get(ErpSyncState, 1)
        if state is None:
            raise RuntimeError("Run Alembic migrations first.")
        if state.ready:
            print("ERP cutover is already complete; use normal ERP synchronization.")
            return
        tables = {
            kind: list((await session.scalars(select(model).order_by(model.id))).all())
            for kind, model in MODELS.items()
        }
        active = list(
            (
                await session.scalars(
                    select(Appointment).where(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
                )
            ).all()
        )
        # Existing window bookings need a stable shared-slot reference as well.
        for appt in active:
            if appt.slot_id:
                continue
            candidates = [
                s
                for s in tables["slots"]
                if s.doctor_id == appt.doctor_id
                and s.start_time == appt.start_time
                and s.end_time == appt.end_time
            ]
            if candidates:
                slot = candidates[0]
            else:
                if any(
                    s.doctor_id == appt.doctor_id
                    and s.start_time < appt.end_time
                    and appt.start_time < s.end_time
                    for s in tables["slots"]
                ):
                    raise RuntimeError(
                        f"Overlapping legacy interval for appointment {appt.id}; "
                        "cutover aborted without deleting data."
                    )
                slot = DoctorSlot(
                    doctor_id=appt.doctor_id,
                    start_time=appt.start_time,
                    end_time=appt.end_time,
                    end_with_buffer=appt.end_time,
                    buffer_minutes=0,
                    capacity=1,
                    is_open=False,
                    version=1,
                )
                session.add(slot)
                await session.flush()
                tables["slots"].append(slot)
            appt.slot_id = slot.id
        for row in tables["slots"]:
            row.buffer_minutes = 0
            row.end_with_buffer = row.end_time
        for row in tables["appointment_types"]:
            row.buffer_minutes = 0
        for kind, items in tables.items():
            for row in items:
                if not row.erp_id:
                    row.erp_id = (
                        row.erp_doctor_id if kind == "doctors" else None
                    ) or f"CB-{kind}-{row.id}"
        maps = {kind: {r.id: r.erp_id for r in items} for kind, items in tables.items()}
        catalog = {}
        for kind, items in tables.items():
            values = []
            for row in items:
                data = {
                    c.name: serialize(getattr(row, c.name))
                    for c in row.__table__.columns
                    if c.name not in EXCLUDE
                }
                for key, target in REFS.items():
                    if key in data and data[key] is not None:
                        data[key] = maps[target][data[key]]
                if kind == "doctors":
                    data.pop("hospital_id", None)  # derived from department
                if kind == "slots":
                    values.append({"id": row.erp_id, **data})
                else:
                    values.append({"id": row.erp_id, "data": data})
            catalog[kind] = values
        bookings = []
        for appt in active:
            appt.erp_booking_id = appt.erp_booking_id or f"ERP-MIG-{appt.id}"
            bookings.append(
                dict(
                    booking_reference=appt.booking_reference,
                    erp_booking_id=appt.erp_booking_id,
                    erp_doctor_id=maps["doctors"][appt.doctor_id],
                    patient_ref=f"P{appt.patient_id}",
                    start_time=appt.start_time.isoformat(),
                    end_time=appt.end_time.isoformat(),
                    status=appt.status,
                    check_in_status=appt.check_in_status,
                    reason=appt.status_reason,
                    slot_id=maps["slots"][appt.slot_id],
                    slot_version=next(s.version for s in tables["slots"] if s.id == appt.slot_id),
                )
            )
        print(
            {kind: len(values) for kind, values in catalog.items()},
            "active bookings:",
            len(bookings),
        )
        if not apply:
            await session.rollback()
            print(
                "Dry run only. Stop backend workers before rerunning with --apply. "
                "No records committed."
            )
            return
        # ERP bootstrap is idempotent: crash between remote import and local commit can retry.
        async with httpx.AsyncClient(base_url=settings.erp_base_url, timeout=60) as client:
            response = await client.post(
                "/simulate/bootstrap", json={"catalog": catalog, "bookings": bookings}
            )
            response.raise_for_status()
            remote = (await client.get("/catalog")).json()
            remote_bookings = (
                await client.get("/bookings", params={"limit": max(100, len(bookings))})
            ).json()
            for item in bookings:

                def same(b, item=item):
                    return all(
                        (datetime.fromisoformat(b[k]) == datetime.fromisoformat(v))
                        if k in ("start_time", "end_time")
                        else b.get(k) == v
                        for k, v in item.items()
                    )

                if not any(same(b) for b in remote_bookings):
                    raise RuntimeError("Booking verification failed; cutover gate remains closed.")
            for kind, values in catalog.items():
                if {r["id"] for r in remote[kind]} != {r["id"] for r in values}:
                    raise RuntimeError("Catalog identity verification failed; gate remains closed.")
        await session.commit()
        erp = HttpErpAdapter(settings.erp_base_url, 60)
        try:
            await sync_catalog(session, erp, cutover=True)
            state = await session.get(ErpSyncState, 1)
            state.ready = True
            await session.commit()
        finally:
            await erp.aclose()
        print("ERP cutover complete. Local IDs, payments, history and payment deadlines preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(run(parser.parse_args().apply))
