"""Client for the `mock-payment` sandbox gateway. Callbacks are HMAC-signed over
"{X-Mock-Timestamp}.{raw body}" with PAYMENT_WEBHOOK_SECRET."""

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Literal

import httpx
from pydantic import AwareDatetime, BaseModel, ValidationError

from app.core.config import settings
from app.core.security import verify_signature
from app.integrations.payment.base import (
    CheckoutRequest,
    CheckoutSession,
    InvalidCallbackError,
    PaymentEvent,
    PaymentGateway,
    PaymentGatewayError,
)


class _CallbackPayload(BaseModel):
    event_id: str
    provider_reference: str
    merchant_payment_id: str
    status: Literal["SUCCEEDED", "FAILED"]
    amount: Decimal
    currency: str
    occurred_at: AwareDatetime
    failure_reason: str | None = None


class MockPaymentGateway(PaymentGateway):
    name = "mock"

    def __init__(self, base_url: str, webhook_secret: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._secret = webhook_secret

    async def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        try:
            response = await self._client.post(
                "/api/checkouts",
                json={
                    "merchant_payment_id": request.merchant_payment_id,
                    "amount": str(request.amount),
                    "currency": request.currency,
                    "description": request.description,
                    "return_url": request.return_url,
                    "callback_url": request.callback_url,
                },
            )
        except httpx.HTTPError as exc:
            raise PaymentGatewayError(str(exc)) from exc
        if response.status_code != 201:
            raise PaymentGatewayError(f"Gateway returned HTTP {response.status_code}")
        data = response.json()
        return CheckoutSession(
            provider_reference=data["provider_reference"], checkout_url=data["checkout_url"]
        )

    def parse_callback(self, body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        if not verify_signature(
            self._secret,
            headers.get("x-mock-timestamp"),
            body,
            headers.get("x-mock-signature"),
            settings.webhook_tolerance_seconds,
        ):
            raise InvalidCallbackError("Invalid callback signature.")
        try:
            payload = _CallbackPayload.model_validate_json(body)
        except ValidationError as exc:
            raise InvalidCallbackError("Malformed callback payload.") from exc
        occurred_at: datetime = payload.occurred_at
        return PaymentEvent(
            event_id=payload.event_id,
            provider_reference=payload.provider_reference,
            merchant_payment_id=payload.merchant_payment_id,
            succeeded=payload.status == "SUCCEEDED",
            amount=payload.amount,
            currency=payload.currency,
            occurred_at=occurred_at,
            failure_reason=payload.failure_reason,
        )

    async def refund(self, provider_reference: str, amount: Decimal) -> str:
        try:
            response = await self._client.post(
                "/api/refunds",
                json={"provider_reference": provider_reference, "amount": str(amount)},
            )
        except httpx.HTTPError as exc:
            raise PaymentGatewayError(str(exc)) from exc
        if response.status_code != 201:
            raise PaymentGatewayError(f"Refund failed with HTTP {response.status_code}")
        return str(response.json()["refund_reference"])

    async def aclose(self) -> None:
        await self._client.aclose()
