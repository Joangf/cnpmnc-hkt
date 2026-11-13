"""Transactional ERP mirrors. Stable upstream IDs preserve all local references."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.errors import AppError, Conflict, ErpUnavailable
from app.models import (
    Appointment,
    AppointmentType,
    Department,
    Doctor,
    DoctorSlot,
    ErpSyncState,
    Hospital,
    Specialty,
)
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, SchedulingMode
from app.schemas.admin import (
    AppointmentTypeCreate,
    DepartmentCreate,
    DoctorCreate,
    HospitalCreate,
    SpecialtyCreate,
)
from app.schemas.slots import SlotCreate
from app.services import audit

MODELS = {
    "hospitals": Hospital,
    "specialties": Specialty,
    "departments": Department,
    "doctors": Doctor,
    "appointment_types": AppointmentType,
    "slots": DoctorSlot,
}
SCHEMAS = {
    "hospitals": HospitalCreate,
    "specialties": SpecialtyCreate,
    "departments": DepartmentCreate,
    "doctors": DoctorCreate,
    "appointment_types": AppointmentTypeCreate,
}
REFS = {
    "hospital_id": "hospitals",
    "specialty_id": "specialties",
    "department_id": "departments",
    "doctor_id": "doctors",
}


async def require_ready(session):
    state = await session.get(ErpSyncState, 1)
    if state is None or not state.ready:
        raise ErpUnavailable("ERP migration is not complete. Booking is temporarily unavailable.")
    return state


async def sync_catalog(session, erp, *, cutover=False):
    if not cutover:
        await require_ready(session)
    try:
        payload = await erp.get_catalog()
    except Exception as exc:
        raise ErpUnavailable("ERP catalog is unavailable; previous data was preserved.") from exc
    if set(payload) != set(MODELS) or any(not isinstance(v, list) for v in payload.values()):
        raise ErpUnavailable("Incomplete ERP catalog; previous data is preserved.")
    now = datetime.now(UTC)
    maps = {}
    try:
        # Serializes sync and booking through doctor locks; one atomic snapshot.
        await session.execute(select(Doctor.id).order_by(Doctor.id).with_for_update())
        for kind, model in MODELS.items():
            maps[kind] = {
                row.erp_id: row
                for row in (await session.scalars(select(model))).all()
                if row.erp_id
            }
            seen = set()
            for item in payload[kind]:
                external = item["id"]
                if not isinstance(external, str) or not 0 < len(external) <= 64 or external in seen:
                    raise ValueError("Invalid or duplicate ERP ID")
                seen.add(external)
                values = dict(item if kind == "slots" else item["data"])
                values.pop("id", None)
                for key, target in REFS.items():
                    if key in values and values[key] is not None:
                        values[key] = maps[target][values[key]].id
                active = values.pop("is_active", True)
                values.pop("buffer_minutes", None)
                if kind == "slots":
                    version = values.pop("version")
                    booked = values.pop("booked_count", 0)
                    doctor_id = values.pop("doctor_id")
                    if type(version) is not int or version < 1 or type(booked) is not int or booked < 0:
                        raise ValueError("Invalid slot revision or occupancy")
                    values = SlotCreate.model_validate(values).model_dump()
                    values.update(
                        doctor_id=doctor_id,
                        version=version,
                        erp_booked_count=booked,
                        buffer_minutes=0,
                        end_with_buffer=values["end_time"],
                    )
                else:
                    values = SCHEMAS[kind].model_validate(values).model_dump()
                    if kind == "appointment_types":
                        values["buffer_minutes"] = 0
                    values["is_active"] = active
                    if kind == "doctors":
                        values.update(scheduling_mode=SchedulingMode.ERP, erp_doctor_id=external)
                        department = await session.get(Department, values["department_id"])
                        values["hospital_id"] = department.hospital_id
                row = maps[kind].get(external)
                if row is None:
                    row = model(erp_id=external, **values)
                    session.add(row)
                    maps[kind][external] = row
                else:
                    if kind == "slots":
                        count = await session.scalar(
                            select(func.count(Appointment.id)).where(
                                Appointment.slot_id == row.id,
                                Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
                            )
                        )
                        if count and any(
                            getattr(row, k) != values[k]
                            for k in ("doctor_id", "start_time", "end_time")
                        ):
                            raise Conflict(
                                "ERP changed a booked slot interval; "
                                "resolve the conflict at the hospital."
                            )
                    for key, value in values.items():
                        setattr(row, key, value)
                row.synced_at = now
                if kind == "doctors":
                    row.updated_at = now
                await session.flush()
            # Explicit is_active/is_open flags control deactivation; absence never deletes history.
        state = await session.get(ErpSyncState, 1)
        state.synced_at = now
        audit.record(
            session,
            "erp.catalog_synced",
            "integration",
            1,
            details={"doctors": len(payload["doctors"])},
        )
        await session.commit()
        return len(payload["doctors"]), 0
    except Exception as exc:
        await session.rollback()
        if isinstance(exc, AppError):
            raise
        raise ErpUnavailable("ERP catalog is invalid; previous data was preserved.") from exc


async def refresh_occupancy(session, erp, slot_id):
    """Refresh the advisory mirror after a booking mutation; ERP remains authoritative."""
    if slot_id is None:
        return
    row = await session.get(DoctorSlot, slot_id)
    if row is None or not row.erp_id:
        return
    try:
        payload = await erp.get_catalog()
        remote = next(item for item in payload["slots"] if item["id"] == row.erp_id)
        count = remote["booked_count"]
        if type(count) is int and count >= 0:
            row.erp_booked_count = count
    except Exception:
        # A successful cancellation must not be reported as failed because browsing refresh failed.
        import structlog
        structlog.get_logger(__name__).warning("erp_occupancy_refresh_failed", slot_id=slot_id)
