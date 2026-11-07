import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import RequestContextMiddleware
from app.core.redis import redis_client
from app.integrations import build_erp_adapter
from app.services.jobs import start_background_jobs

configure_logging()
logger = structlog.get_logger("app")

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Registration, sign-in, token refresh, password reset (FR-ACC).",
    },
    {"name": "profile", "description": "Patient profile (FR-PRO)."},
    {
        "name": "directory",
        "description": "Hospitals, clinics, departments, doctors (FR-DIS, FR-CLN).",
    },
    {"name": "availability", "description": "Bookable slots (FR-BOOK-02)."},
    {
        "name": "symptoms",
        "description": "Rule-based specialty recommendation - not a diagnosis (FR-REC).",
    },
    {
        "name": "appointments",
        "description": "Booking and appointment management (FR-BOOK, FR-APT, FR-HIS).",
    },
    {
        "name": "payments",
        "description": "VietQR bank-transfer payments via SePay (FR-PAY). Status is separate "
        "from appointment status.",
    },
    {"name": "refunds", "description": "Patient refund requests and manual admin payouts."},
    {"name": "reviews", "description": "Doctor reviews (FR-REV)."},
    {"name": "notifications", "description": "In-app notifications (FR-NOT)."},
    {"name": "integrations", "description": "Inbound ERP/HIS webhooks (FRD 3.2)."},
    {"name": "admin", "description": "Administration, moderation, reporting (FR-ADM, FR-RPT)."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.erp = build_erp_adapter()
    tasks = start_background_jobs(app) if settings.run_background_jobs else []
    logger.info("startup", env=settings.env, erp_adapter=app.state.erp.name)
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await app.state.erp.aclose()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="Healthcare Appointment Platform API",
    version="0.1.0",
    description="Patient-facing discovery, booking and payment API. See FRD v1.2.",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)
setup_metrics(app)
app.include_router(api_router, prefix="/api/v1")


def _error(
    request: Request, status_code: int, code: str, message: str, details: list | None = None
) -> JSONResponse:
    body: dict = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content={"error": body})


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return _error(request, exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Do not echo submitted values back (they may contain PII).
    details = [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return _error(request, 422, "ValidationFailed", "The request contains invalid data.", details)


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return _error(request, 500, "InternalError", "An unexpected error occurred.")


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> JSONResponse:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        await redis_client.ping()
    except Exception:
        logger.warning("readiness_check_failed")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})
