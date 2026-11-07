from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, SessionDep
from app.core.config import settings
from app.core.errors import NotFound
from app.models import Doctor
from app.schemas.common import error_responses
from app.schemas.slots import AdminSlotList, AdminSlotOut, SlotCreate, SlotUpdate
from app.services import manual_slots

router = APIRouter(prefix="/admin/doctors/{doctor_id}/slots", tags=["admin"],
                   responses=error_responses(401, 403, 404, 409, 422))


@router.get("", response_model=AdminSlotList, operation_id="adminListDoctorSlots")
async def list_slots(
    doctor_id: int, admin: AdminUser, session: SessionDep,
    day: Annotated[date, Query(alias="date")],
) -> AdminSlotList:
    if await session.get(Doctor, doctor_id) is None:
        raise NotFound("Doctor not found.")
    return AdminSlotList(
        doctor_id=doctor_id, timezone=settings.clinic_timezone,
        slots=[manual_slots.present(slot, count)
               for slot, count in await manual_slots.rows_for_day(session, doctor_id, day)],
    )


@router.post("", response_model=AdminSlotOut, status_code=status.HTTP_201_CREATED,
             operation_id="adminCreateDoctorSlot")
async def create_slot(
    doctor_id: int, payload: SlotCreate, admin: AdminUser, session: SessionDep,
) -> AdminSlotOut:
    return await manual_slots.create(session, doctor_id, payload, admin.id)


@router.patch("/{slot_id}", response_model=AdminSlotOut, operation_id="adminUpdateDoctorSlot")
async def update_slot(
    doctor_id: int, slot_id: int, payload: SlotUpdate, admin: AdminUser, session: SessionDep,
) -> AdminSlotOut:
    return await manual_slots.update(session, doctor_id, slot_id, payload, admin.id)
