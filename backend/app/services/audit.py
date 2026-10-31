from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.models.enums import ActorType, StatusSource

logger = structlog.get_logger(__name__)


def actor_type_for(source: StatusSource) -> ActorType:
    if source == StatusSource.ERP:
        return ActorType.ERP
    if source in (StatusSource.PATIENT, StatusSource.ADMIN):
        return ActorType.USER
    return ActorType.SYSTEM


def record(
    session: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    *,
    actor_id: int | None = None,
    actor_type: ActorType = ActorType.USER,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit row to the current transaction (NFR-10). Never put PII in `details`."""
    if actor_id is None and actor_type == ActorType.USER:
        actor_type = ActorType.SYSTEM
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    session.add(
        AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            request_id=request_id,
        )
    )
    logger.info(
        "audit", action=action, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id
    )
