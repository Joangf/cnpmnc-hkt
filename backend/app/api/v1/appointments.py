from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import presenters
from app.api.deps import CurrentPatient, ErpDep, PageDep, RedisDep, SessionDep
from app.core.errors import NotFound
from app.models import Appointment
from app.repositories import appointments as appointment_repo
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentDetail,
    AppointmentSummary,
    CancelRequest,
)
from app.schemas.common import Page, error_responses
from app.services import booking

router = APIRouter(prefix="/appointments", tags=["appointments"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        max_length=64,
        description="Client-generated key to make retries safe",
    ),
]


async def _load_owned(session: AsyncSession, appointment_id: int, patient_id: int) -> Appointment:
    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient_id:  # BR-12
        raise NotFound("Appointment not found.")
    return appointment


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AppointmentDetail,
    operation_id="createAppointment",
    responses=error_responses(401, 403, 404, 409, 422, 503),
    description=(
        "Revalidates availability, reserves the slot atomically and submits it to the hospital "
        "system. The returned `status` is PENDING, CONFIRMED or REJECTED; only CONFIRMED means "
        "the hospital accepted the booking."
    ),
)
async def create_appointment(
    payload: AppointmentCreate,
    patient: CurrentPatient,
    session: SessionDep,
    redis: RedisDep,
    erp: ErpDep,
    idempotency_key: IdempotencyKey = None,
) -> AppointmentDetail:
    appointment_id = await booking.create_appointment(
        session, redis, erp, patient, payload, idempotency_key
    )
    return presenters.appointment_detail(await _load_owned(session, appointment_id, patient.id))


@router.get(
    "",
    response_model=Page[AppointmentSummary],
    operation_id="listMyAppointments",
    responses=error_responses(401, 403),
)
async def list_my_appointments(
    patient: CurrentPatient,
    session: SessionDep,
    paging: PageDep,
    scope: Annotated[Literal["upcoming", "past", "all"], Query()] = "upcoming",
) -> Page[AppointmentSummary]:
    items, total = await appointment_repo.list_for_patient(
        session, patient.id, scope, datetime.now(UTC), paging.page, paging.page_size
    )
    return Page[AppointmentSummary](
        items=[presenters.appointment_summary(a) for a in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetail,
    operation_id="getMyAppointment",
    responses=error_responses(401, 403, 404),
)
async def get_my_appointment(
    appointment_id: int, patient: CurrentPatient, session: SessionDep
) -> AppointmentDetail:
    return presenters.appointment_detail(await _load_owned(session, appointment_id, patient.id))


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentDetail,
    operation_id="cancelAppointment",
    responses=error_responses(401, 403, 404, 409, 503),
)
async def cancel_appointment(
    appointment_id: int,
    payload: CancelRequest,
    patient: CurrentPatient,
    session: SessionDep,
    redis: RedisDep,
    erp: ErpDep,
) -> AppointmentDetail:
    await booking.cancel_appointment(session, redis, erp, patient, appointment_id, payload.reason)
    return presenters.appointment_detail(await _load_owned(session, appointment_id, patient.id))
