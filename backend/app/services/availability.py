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
from app.repositories import appointments as appointment_repo
from app.services.scheduling import Interval, ScheduleWindow, Slot, generate_slots
from app.services.scheduling_settings import EffectiveSettings, resolve

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
    session: AsyncSession, doctor_id: int, appointment_type: AppointmentType, day: date,
    *, effective: EffectiveSettings | None = None,
) -> list[Slot]:
    """Authoritative-as-possible computation straight from the database (used for BR-03)."""
    if effective is None:
        doctor = await session.get(Doctor, doctor_id)
        if doctor is None:
            return []
        effective = resolve(doctor, appointment_type)
    start, end = day_bounds(day)
    rows = await appointment_repo.schedule_rows(session, doctor_id, start, end)
    windows = [
        ScheduleWindow(r.start_time, r.end_time, effective.window_capacity(r.max_appointments))
        for r in rows if r.is_available
    ]
    blocked = [Interval(r.start_time, r.end_time) for r in rows if not r.is_available]
    busy = [
        Interval(s, e)
        for s, e in await appointment_repo.busy_intervals(
            session, doctor_id,
            min([start, *(r.start_time for r in rows)]),
            max([end, *(r.end_time for r in rows)]),
        )
    ]
    return generate_slots(
        windows,
        busy,
        blocked=blocked,
        duration=effective.duration,
        buffer=effective.buffer,
        increment=timedelta(minutes=settings.slot_increment_minutes),
        not_before=datetime.now(UTC) + timedelta(minutes=settings.booking_min_lead_minutes),
    )


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
    doctor = await session.get(Doctor, doctor_id)
    if doctor is None:
        return []
    effective = resolve(doctor, appointment_type)
    key, field = _cache_key(doctor_id, day), effective.fingerprint
    try:
        cached = await redis.hget(key, field)  # type: ignore[misc]  # redis-py stub union
        if cached:
            return [
                Slot(datetime.fromisoformat(s), datetime.fromisoformat(e))
                for s, e in json.loads(cached)
            ]
    except RedisError:
        logger.warning("availability_cache_read_failed")

    slots = await compute_slots(session, doctor_id, appointment_type, day, effective=effective)
    try:
        payload = json.dumps([[s.start.isoformat(), s.end.isoformat()] for s in slots])
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
