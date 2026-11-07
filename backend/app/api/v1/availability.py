import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import RedisDep, SessionDep
from app.core.config import settings
from app.core.errors import NotFound
from app.models.enums import SchedulingMode
from app.repositories import directory as directory_repo
from app.schemas.common import error_responses
from app.schemas.directory import AvailabilityResponse, SlotOut
from app.services import availability, policies
from app.services.scheduling_settings import select_type

router = APIRouter(tags=["availability"])


@router.get(
    "/doctors/{doctor_id}/availability",
    response_model=AvailabilityResponse,
    operation_id="getDoctorAvailability",
    responses=error_responses(404, 422),
)
async def get_doctor_availability(
    doctor_id: int,
    session: SessionDep,
    redis: RedisDep,
    day: Annotated[dt.date, Query(alias="date", description="Clinic-local date (YYYY-MM-DD)")],
    appointment_type_id: int | None = Query(default=None),
) -> AvailabilityResponse:
    doctor = await directory_repo.get_doctor(session, doctor_id)
    if doctor is None or not policies.doctor_is_published(doctor):
        raise NotFound("Doctor not found.")
    appointment_type = await select_type(session, doctor, appointment_type_id)

    availability.check_booking_window(day)

    slots = await availability.get_slots_cached(session, redis, doctor.id, appointment_type, day)
    return AvailabilityResponse(
        doctor_id=doctor.id,
        date=day,
        appointment_type_id=appointment_type.id,
        timezone=settings.clinic_timezone,
        slots=[SlotOut(start_time=s.start, end_time=s.end, slot_id=s.slot_id, version=s.version,
                       capacity=s.capacity, remaining_places=s.remaining_places) for s in slots],
        generated_at=dt.datetime.now(dt.UTC),
        source="manual-slots" if doctor.scheduling_mode == SchedulingMode.MANUAL
        else "erp-schedule-cache",
    )
