"""Payment workflow (FRD 4.10). Payment status never implies appointment status (BR-07)."""

from collections.abc import Mapping
from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    InvalidState,
    NotFound,
    PaymentGatewayUnavailable,
    Unauthorized,
    ValidationFailed,
)
from app.core.metrics import PAYMENTS
from app.integrations.payment.base import (
    CheckoutRequest,
    InvalidCallbackError,
    PaymentGateway,
    PaymentGatewayError,
)
from app.models import Appointment, PatientProfile, Payment
from app.models.enums import ActorType, NotificationType, PaymentStatus
from app.repositories import appointments as appointment_repo
from app.repositories import payments as payment_repo
from app.services import audit, idempotency, notifications, policies

logger = structlog.get_logger(__name__)


async def initiate_payment(
    session: AsyncSession,
    redis: Redis,
    gateway: PaymentGateway,
    patient: PatientProfile,
    appointment_id: int,
    idempotency_key: str | None,
) -> Payment:
    user_id = patient.user_id
    if idempotency_key:
        existing = await idempotency.begin(redis, "payment", user_id, idempotency_key)
        if existing:
            payment = await payment_repo.get(session, int(existing))
            if payment is not None:
                return payment
    try:
        payment = await _initiate(session, gateway, patient, appointment_id)
    except Exception:
        if idempotency_key:
            await idempotency.release(redis, "payment", user_id, idempotency_key)
        raise
    if idempotency_key:
        await idempotency.complete(redis, "payment", user_id, idempotency_key, payment.id)
    return payment


async def _initiate(
    session: AsyncSession, gateway: PaymentGateway, patient: PatientProfile, appointment_id: int
) -> Payment:
    appointment = await appointment_repo.get_detail(session, appointment_id)
    if appointment is None or appointment.patient_id != patient.id:
        raise NotFound("Appointment not found.")
    if appointment.fee_amount <= 0:
        raise InvalidState("This appointment has no payable fee.", code="PaymentNotRequired")
    if not policies.payment_allowed_for_status(appointment.status):
        raise InvalidState(
            "Payment becomes available once the hospital has confirmed the appointment.",
            code="PaymentNotAllowed",
        )
    if policies.payment_status_of(appointment.payments) in (
        PaymentStatus.PAID,
        PaymentStatus.REFUNDED,
    ):
        raise InvalidState("This appointment has already been paid.", code="AlreadyPaid")

    # FR-PAY-06 retry: older unfinished attempts are superseded by the new one.
    for previous in appointment.payments:
        if previous.status == PaymentStatus.PENDING:
            previous.status = PaymentStatus.FAILED
            previous.failure_reason = "Superseded by a new payment attempt."

    payment = Payment(
        appointment_id=appointment.id,
        amount=appointment.fee_amount,
        currency=appointment.currency,
        status=PaymentStatus.PENDING,
        provider=gateway.name,
    )
    session.add(payment)
    await session.flush()

    try:
        checkout = await gateway.create_checkout(
            CheckoutRequest(
                merchant_payment_id=str(payment.id),
                amount=payment.amount,
                currency=payment.currency,
                description=f"Appointment {appointment.booking_reference}",
                return_url=f"{settings.public_base_url}/payments/result?payment_id={payment.id}",
                callback_url=f"{settings.internal_base_url}/api/v1/payments/callback",
            )
        )
    except PaymentGatewayError as exc:
        await session.rollback()
        logger.warning("payment_gateway_unavailable", appointment_id=appointment_id)
        raise PaymentGatewayUnavailable() from exc

    payment.provider_reference = checkout.provider_reference
    payment.checkout_url = checkout.checkout_url
    audit.record(
        session,
        "payment.initiated",
        "payment",
        payment.id,
        actor_id=patient.user_id,
        details={"appointment_id": appointment.id, "amount": str(payment.amount)},
    )
    await session.commit()
    PAYMENTS.labels(status=PaymentStatus.PENDING).inc()
    return payment


async def handle_callback(
    session: AsyncSession, gateway: PaymentGateway, body: bytes, headers: Mapping[str, str]
) -> str:
    """Validate and apply a gateway callback (FR-PAY-03/04, NFR-11). Idempotent."""
    try:
        event = gateway.parse_callback(body, headers)
    except InvalidCallbackError as exc:
        logger.warning("payment_callback_rejected", reason=str(exc))
        raise Unauthorized("Invalid payment callback.", code="InvalidSignature") from exc

    payment = await payment_repo.get_by_provider_reference_for_update(
        session, event.provider_reference
    )
    if payment is None or str(payment.id) != event.merchant_payment_id:
        raise NotFound("Unknown payment.")
    if payment.last_event_id == event.event_id:
        await session.rollback()
        return "duplicate"
    if event.amount != payment.amount or event.currency != payment.currency:
        logger.error("payment_amount_mismatch", payment_id=payment.id)
        raise ValidationFailed("Payment amount does not match.", code="AmountMismatch")

    new_status = PaymentStatus.PAID if event.succeeded else PaymentStatus.FAILED
    if (
        payment.status in (PaymentStatus.PAID, PaymentStatus.REFUNDED)
        and new_status == PaymentStatus.FAILED
    ):
        await session.rollback()
        return "ignored"

    old_status = payment.status
    payment.last_event_id = event.event_id
    payment.status = new_status
    if new_status == PaymentStatus.PAID:
        payment.paid_at = event.occurred_at
        payment.failure_reason = None
        if old_status == PaymentStatus.FAILED:
            logger.warning("payment_paid_after_supersede", payment_id=payment.id)
    else:
        payment.failure_reason = event.failure_reason or "The payment was declined."

    audit.record(
        session,
        "payment.status_changed",
        "payment",
        payment.id,
        actor_type=ActorType.PAYMENT_GATEWAY,
        details={"from": old_status, "to": new_status, "provider_event_id": event.event_id},
    )
    appointment = payment.appointment
    if new_status == PaymentStatus.PAID:
        title = "Payment successful"
        content = f"We received your payment for appointment {appointment.booking_reference}."
    else:
        title = "Payment failed"
        content = (
            f"Your payment for appointment {appointment.booking_reference} did not go through. "
            "You can try again from the appointment page."
        )
    await notifications.notify_patient(  # FR-NOT-03
        session,
        appointment.patient_id,
        NotificationType.PAYMENT_RESULT,
        title,
        content,
        f"/appointments/{appointment.id}",
    )
    await session.commit()
    PAYMENTS.labels(status=new_status).inc()
    return "processed"


async def refund_if_paid(
    session: AsyncSession, gateway: PaymentGateway, appointment: Appointment
) -> None:
    """FR-PAY-07 (Could): refund on cancellation if the policy allows (OQ-09)."""
    if not settings.refund_on_cancellation:
        return
    paid = next((p for p in appointment.payments if p.status == PaymentStatus.PAID), None)
    if paid is None or paid.provider_reference is None:
        return
    try:
        refund_reference = await gateway.refund(paid.provider_reference, paid.amount)
    except PaymentGatewayError:
        logger.error("refund_failed", payment_id=paid.id)
        audit.record(
            session, "payment.refund_failed", "payment", paid.id, actor_type=ActorType.SYSTEM
        )
        await notifications.notify_patient(
            session,
            appointment.patient_id,
            NotificationType.PAYMENT_RESULT,
            "Refund pending",
            f"We could not refund appointment {appointment.booking_reference} automatically. "
            "Our team will follow up.",
            f"/appointments/{appointment.id}",
        )
        await session.commit()
        return

    paid.status = PaymentStatus.REFUNDED
    paid.refunded_at = datetime.now(UTC)
    audit.record(
        session,
        "payment.refunded",
        "payment",
        paid.id,
        actor_type=ActorType.PAYMENT_GATEWAY,
        details={"refund_reference": refund_reference},
    )
    await notifications.notify_patient(
        session,
        appointment.patient_id,
        NotificationType.PAYMENT_RESULT,
        "Refund issued",
        f"Your payment for appointment {appointment.booking_reference} has been refunded.",
        f"/appointments/{appointment.id}",
    )
    await session.commit()
    PAYMENTS.labels(status=PaymentStatus.REFUNDED).inc()


async def get_for_patient(
    session: AsyncSession, patient: PatientProfile, payment_id: int
) -> Payment:
    payment = await payment_repo.get(session, payment_id)
    if payment is None or payment.appointment.patient_id != patient.id:
        raise NotFound("Payment not found.")
    return payment
