"""In-process periodic jobs (schedule sync, pending reconciliation).

A Redis lock ensures only one backend replica runs each job per interval.
"""

import asyncio
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.redis import redis_client
from app.services import erp_sync

logger = structlog.get_logger(__name__)

Job = Callable[[AsyncSession], Awaitable[bool]]
_RETRY_SECONDS = 15


async def _run_periodic(name: str, interval: int, job: Job) -> None:
    lock_key = f"job-lock:{name}"
    while True:
        delay = interval
        try:
            if await redis_client.set(lock_key, "1", nx=True, ex=max(interval - 1, 1)):
                async with SessionLocal() as session:
                    ok = await job(session)
                if not ok:
                    # Release early so a failing first run (e.g. ERP still booting) retries soon.
                    await redis_client.delete(lock_key)
                    delay = _RETRY_SECONDS
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("background_job_failed", job=name)
            delay = _RETRY_SECONDS
        await asyncio.sleep(delay)


def start_background_jobs(app: FastAPI) -> list[asyncio.Task[None]]:
    erp = app.state.erp
    return [
        asyncio.create_task(
            _run_periodic(
                "schedule-sync",
                settings.schedule_sync_interval_seconds,
                lambda s: erp_sync.sync_schedules(s, erp),
            )
        ),
        asyncio.create_task(
            _run_periodic(
                "reconcile-pending",
                settings.reconcile_interval_seconds,
                lambda s: erp_sync.reconcile_pending(s, erp),
            )
        ),
    ]
