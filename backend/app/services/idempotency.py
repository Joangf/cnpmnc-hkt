"""Idempotency-Key handling for booking and payment initiation (double-submit protection)."""

from redis.asyncio import Redis

from app.core.errors import Conflict

_IN_PROGRESS = "__in_progress__"
_LOCK_SECONDS = 60
_RESULT_SECONDS = 24 * 3600


def _key(scope: str, owner_id: int, key: str) -> str:
    return f"idem:{scope}:{owner_id}:{key}"


async def begin(redis: Redis, scope: str, owner_id: int, key: str) -> str | None:
    """Return the stored resource id if this key already completed, else take the lock."""
    redis_key = _key(scope, owner_id, key)
    existing = await redis.get(redis_key)
    if existing and existing != _IN_PROGRESS:
        return str(existing)
    if existing == _IN_PROGRESS or not await redis.set(
        redis_key, _IN_PROGRESS, nx=True, ex=_LOCK_SECONDS
    ):
        raise Conflict(
            "A request with this Idempotency-Key is still being processed.",
            code="IdempotencyInProgress",
        )
    return None


async def complete(redis: Redis, scope: str, owner_id: int, key: str, resource_id: int) -> None:
    await redis.set(_key(scope, owner_id, key), str(resource_id), ex=_RESULT_SECONDS)


async def release(redis: Redis, scope: str, owner_id: int, key: str) -> None:
    await redis.delete(_key(scope, owner_id, key))
