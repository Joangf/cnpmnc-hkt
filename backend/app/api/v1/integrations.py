"""Inbound ERP/HIS webhooks (FRD 3.2, 5.4)."""

from fastapi import APIRouter, Request
from pydantic import ValidationError

from app.api.deps import RedisDep, SessionDep
from app.core.config import settings
from app.core.errors import Unauthorized, ValidationFailed
from app.core.security import verify_signature
from app.schemas.common import error_responses
from app.schemas.integrations import ErpEvent, WebhookAck
from app.services import erp_sync

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post(
    "/erp/events",
    response_model=WebhookAck,
    operation_id="receiveErpEvent",
    responses=error_responses(401, 404, 409, 422),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": ErpEvent.model_json_schema()}},
        }
    },
    description=(
        "Status changes pushed by the hospital ERP/HIS. Requires X-Erp-Timestamp and "
        "X-Erp-Signature = hex(HMAC-SHA256(secret, '{timestamp}.{raw body}')). "
        "Idempotent per event_id."
    ),
)
async def receive_erp_event(request: Request, session: SessionDep, redis: RedisDep) -> WebhookAck:
    body = await request.body()
    if not verify_signature(
        settings.erp_webhook_secret,
        request.headers.get("x-erp-timestamp"),
        body,
        request.headers.get("x-erp-signature"),
        settings.webhook_tolerance_seconds,
    ):
        raise Unauthorized("Invalid webhook signature.", code="InvalidSignature")
    try:
        event = ErpEvent.model_validate_json(body)
    except ValidationError as exc:
        raise ValidationFailed("Malformed ERP event.") from exc

    dedup_key = f"erp:event:{event.event_id}"
    if not await redis.set(dedup_key, "1", nx=True, ex=86400):
        return WebhookAck(status="duplicate")
    try:
        result = await erp_sync.handle_event(session, redis, event)
    except Exception:
        await redis.delete(dedup_key)  # allow the ERP to retry
        raise
    return WebhookAck(status=result)  # type: ignore[arg-type]
