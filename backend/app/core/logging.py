"""Structured JSON logging to stdout (collected by Alloy -> Loki).

A redaction processor strips PII from every log event (NFR-03, NFR-04).
"""

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings

PII_KEYS = frozenset(
    {
        "password",
        "new_password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "email",
        "full_name",
        "phone",
        "phone_number",
        "date_of_birth",
        "dob",
        "address",
        "symptoms",
        "free_text",
        "reason_for_visit",
        "comment",
    }
)
REDACTED = "[REDACTED]"


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: REDACTED if str(k).lower() in PII_KEYS else _scrub(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub(v) for v in value]
    return value


def redact_pii(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return _scrub(event_dict)


def add_service(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("service", settings.service_name)
    return event_dict


def configure_logging() -> None:
    level = logging.getLevelName(settings.log_level.upper())
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_service,
        redact_pii,
    ]

    structlog.configure(
        processors=[
            *shared,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, httpx) through the same JSON pipeline.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
    # Access logs are emitted by RequestContextMiddleware instead.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("httpx").setLevel(logging.WARNING)
