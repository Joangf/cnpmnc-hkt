"""Effective scheduling rules shared by offers and reservations (SCRUM-21)."""

import json
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailed
from app.models import AppointmentType, Doctor
from app.repositories import directory as directory_repo


async def select_type(
    session: AsyncSession, doctor: Doctor, type_id: int | None
) -> AppointmentType:
    from app.services.policies import type_applies_to_doctor

    if type_id is None:
        types = await directory_repo.list_appointment_types_for_doctor(session, doctor)
        appointment_type = types[0] if types else None
    else:
        appointment_type = await session.get(AppointmentType, type_id)
    if appointment_type is None or not type_applies_to_doctor(appointment_type, doctor):
        raise ValidationFailed("This appointment type is not offered by the selected doctor.")
    return appointment_type


@dataclass(frozen=True, slots=True)
class EffectiveSettings:
    duration: timedelta
    buffer: timedelta
    capacity: int
    fingerprint: str

    def window_capacity(self, erp_limit: int | None) -> int:
        if erp_limit is None:
            return self.capacity
        # Malformed ERP limits must never remove the local capacity restriction.
        if type(erp_limit) is not int or erp_limit <= 0:
            return 0
        return min(self.capacity, erp_limit)


def resolve(doctor: Doctor, appointment_type: AppointmentType) -> EffectiveSettings:
    duration, buffer = appointment_type.duration_minutes, appointment_type.buffer_minutes
    capacity = doctor.max_appointments_per_window
    if capacity is None:
        capacity = 1  # Matches the migration, database default and seed policy.
    if (
        type(duration) is not int or not 5 <= duration <= 480
        or type(buffer) is not int or not 0 <= buffer <= 120
        or type(capacity) is not int or capacity <= 0
    ):
        raise ValidationFailed("Scheduling settings are invalid; contact an administrator.")
    fingerprint = json.dumps([
        appointment_type.id, duration, buffer, capacity,
        str(appointment_type.updated_at), str(doctor.updated_at),
    ])
    return EffectiveSettings(
        timedelta(minutes=duration), timedelta(minutes=buffer), capacity, fingerprint
    )
