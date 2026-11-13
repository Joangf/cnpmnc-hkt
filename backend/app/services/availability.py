"""Availability for a doctor/day/appointment type, from the synced schedule cache plus
local slot-holding appointments (FR-BOOK-02)."""

import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ValidationFailed
from app.models import AppointmentType, Doctor
from app.services.scheduling import Slot
from app.services.scheduling_settings import EffectiveSettings

logger = structlog.get_logger(__name__)


def clinic_tz() -> ZoneInfo:
    return ZoneInfo(settings.clinic_timezone)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    tz = clinic_tz()
    return (
        datetime.combine(day, time.min, tzinfo=tz),
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz),
    )


def local_day(moment: datetime) -> date:
    return moment.astimezone(clinic_tz()).date()


def format_local(moment: datetime) -> str:
    return moment.astimezone(clinic_tz()).strftime("%d/%m/%Y %H:%M")


def check_booking_window(day: date, now: datetime | None = None) -> None:
    today = local_day(now or datetime.now(UTC))
    if day < today:
        raise ValidationFailed("The selected date is in the past.", code="DateOutOfRange")
    if day > today + timedelta(days=settings.booking_horizon_days):
        raise ValidationFailed(
            f"Appointments can be booked up to {settings.booking_horizon_days} days ahead.",
            code="DateOutOfRange",
        )


async def compute_slots(
    session: AsyncSession,
    doctor_id: int,
    appointment_type: AppointmentType,
    day: date,
    *,
    effective: EffectiveSettings | None = None,
    include_past: bool = False,
) -> list[Slot]:
    """Authoritative-as-possible computation straight from the database (used for BR-03)."""
    doctor = await session.get(Doctor, doctor_id)
    if doctor is None:
        return []
    from app.models import ErpSyncState
    from app.services.manual_slots import offers

    state = await session.get(ErpSyncState, 1)
    if not state or not state.ready:
        return []
    return await offers(session, doctor_id, day, include_past=include_past)


def _cache_key(doctor_id: int, day: date) -> str:
    return f"avail:{doctor_id}:{day.isoformat()}"


async def get_slots_cached(
    session: AsyncSession,
    redis: Redis,
    doctor_id: int,
    appointment_type: AppointmentType,
    day: date,
) -> list[Slot]:
    """Short-TTL cache for browsing. Never used for booking validation."""
    from app.models import ErpSyncState

    state = await session.get(ErpSyncState, 1)
    if not state or not state.ready:
        return []
    doctor = await session.get(Doctor, doctor_id)
    if doctor is None:
        return []
    effective = None
    fingerprint = json.dumps(
        [
            appointment_type.id,
            str(appointment_type.updated_at),
            str(doctor.updated_at),
        ]
    )
    key = _cache_key(doctor_id, day)
    field = f"v4:{doctor.scheduling_mode}:{fingerprint}"
    not_before = datetime.now(UTC) + timedelta(minutes=settings.booking_min_lead_minutes)
    try:
        cached = await redis.hget(key, field)  # type: ignore[misc]  # redis-py stub union
        if cached:
            slots_cached = []
            for s in json.loads(cached):
                s_start = datetime.fromisoformat(s["start"])
                slots_cached.append(
                    Slot(
                        s_start,
                        datetime.fromisoformat(s["end"]),
                        s["slot_id"],
                        s["version"],
                        s["capacity"],
                        s["remaining_places"],
                        is_past=s_start < not_before,
                    )
                )
            return slots_cached
    except RedisError:
        logger.warning("availability_cache_read_failed")

    slots = await compute_slots(
        session, doctor_id, appointment_type, day, effective=effective, include_past=True
    )
    try:
        payload = json.dumps(
            [
                {
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                    "slot_id": s.slot_id,
                    "version": s.version,
                    "capacity": s.capacity,
                    "remaining_places": s.remaining_places,
                }
                for s in slots
            ]
        )
        async with redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, field, payload)
            pipe.expire(key, settings.availability_cache_seconds)
            await pipe.execute()
    except RedisError:
        logger.warning("availability_cache_write_failed")
    return slots


async def invalidate(redis: Redis, doctor_id: int, *days: date) -> None:
    try:
        await redis.delete(*(_cache_key(doctor_id, d) for d in days))
    except RedisError:
        logger.warning("availability_cache_invalidate_failed")
