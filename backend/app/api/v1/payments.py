from typing import Annotated

from fastapi import APIRouter, Header, Request, status

from app.api import presenters
from app.api.deps import CurrentPatient, GatewayDep, RedisDep, SessionDep
from app.schemas.common import error_responses
from app.schemas.integrations import WebhookAck
from app.schemas.payments import PaymentInitResponse, PaymentOut
from app.services import payments as payment_service

router = APIRouter(tags=["payments"])


@router.post(
    "/appointments/{appointment_id}/payments",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentInitResponse,
    operation_id="initiatePayment",
    responses=error_responses(401, 403, 404, 409, 503),
    description="Creates a payment attempt and returns the gateway checkout URL (FR-PAY-01/02).",
)
async def initiate_payment(
    appointment_id: int,
    patient: CurrentPatient,
    session: SessionDep,
    redis: RedisDep,
    gateway: GatewayDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=64)] = None,
) -> PaymentInitResponse:
    payment = await payment_service.initiate_payment(
        session, redis, gateway, patient, appointment_id, idempotency_key
    )
    return PaymentInitResponse(
        payment_id=payment.id,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        checkout_url=payment.checkout_url or "",
    )


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentOut,
    operation_id="getPayment",
    responses=error_responses(401, 403, 404),
)
async def get_payment(payment_id: int, patient: CurrentPatient, session: SessionDep) -> PaymentOut:
    return presenters.payment_out(
        await payment_service.get_for_patient(session, patient, payment_id)
    )


@router.post(
    "/payments/callback",
    response_model=WebhookAck,
    operation_id="receivePaymentCallback",
    responses=error_responses(401, 404, 422),
    description=(
        "Server-to-server callback from the payment gateway. Signed with "
        "X-Mock-Timestamp / X-Mock-Signature (HMAC-SHA256 over '{timestamp}.{body}')."
    ),
)
async def payment_callback(
    request: Request, session: SessionDep, gateway: GatewayDep
) -> WebhookAck:
    body = await request.body()
    result = await payment_service.handle_callback(session, gateway, body, request.headers)
    return WebhookAck(status=result)  # type: ignore[arg-type]
