import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import RedisDep, SessionDep
from app.core.config import settings
from app.core.errors import NotFound, ValidationFailed
from app.models import AppointmentType
from app.repositories import directory as directory_repo
from app.schemas.common import error_responses
from app.schemas.directory import AvailabilityResponse, SlotOut
from app.services import availability, policies

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
    if doctor is None or not doctor.is_active:
        raise NotFound("Doctor not found.")
    if appointment_type_id is not None:
        appointment_type = await session.get(AppointmentType, appointment_type_id)
        if appointment_type is None or not policies.type_applies_to_doctor(appointment_type, doctor):
            raise ValidationFailed("This appointment type is not offered by the selected doctor.")
    else:
        types = await directory_repo.list_appointment_types_for_doctor(session, doctor)
        if not types:
            raise ValidationFailed("No active appointment types available.")
        appointment_type = types[0]

    availability.check_booking_window(day)

    slots = await availability.get_slots_cached(session, redis, doctor.id, appointment_type, day)
    return AvailabilityResponse(
        doctor_id=doctor.id,
        date=day,
        appointment_type_id=appointment_type.id,
        timezone=settings.clinic_timezone,
        slots=[SlotOut(start_time=s.start, end_time=s.end) for s in slots],
        generated_at=dt.datetime.now(dt.UTC),
        source="erp-schedule-cache",
    )
