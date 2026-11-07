from typing import Annotated

from fastapi import APIRouter, Header, status

from app.api import presenters
from app.api.deps import CurrentPatient, SessionDep
from app.schemas.common import error_responses
from app.schemas.payments import PaymentOut, SepayWebhookAck, SepayWebhookIn
from app.services import payments as payment_service

router = APIRouter(tags=["payments"])


@router.post(
    "/appointments/{appointment_id}/payments",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentOut,
    operation_id="initiatePayment",
    responses=error_responses(401, 403, 404, 409),
    description=(
        "Issues a VietQR bank-transfer payment for a confirmed appointment (FR-PAY-01/02). "
        "Returns the still-open PENDING attempt if there is one, so repeated calls never create "
        "a second payment code. The QR expires at the appointment's payment deadline."
    ),
)
async def initiate_payment(
    appointment_id: int, patient: CurrentPatient, session: SessionDep
) -> PaymentOut:
    payment = await payment_service.initiate_payment(session, patient, appointment_id)
    return presenters.payment_out(payment)


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentOut,
    operation_id="getPayment",
    responses=error_responses(401, 403, 404),
    description="Authoritative payment status, updated by the SePay webhook or poller.",
)
async def get_payment(payment_id: int, patient: CurrentPatient, session: SessionDep) -> PaymentOut:
    return presenters.payment_out(
        await payment_service.get_for_patient(session, patient, payment_id)
    )


@router.post(
    "/payments/sepay-webhook",
    response_model=SepayWebhookAck,
    operation_id="receiveSepayWebhook",
    responses=error_responses(401),
    description=(
        "SePay bank-transaction webhook, authenticated with `Authorization: Apikey <key>`. "
        "Incoming transfers whose content contains a payment code settle that payment. "
        'Always answers {"success": true} for authenticated calls so SePay does not retry.'
    ),
)
async def sepay_webhook(
    payload: SepayWebhookIn,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> SepayWebhookAck:
    await payment_service.handle_webhook(session, payload, authorization)
    return SepayWebhookAck()
