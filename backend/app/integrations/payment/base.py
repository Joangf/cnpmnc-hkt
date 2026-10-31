from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CheckoutRequest:
    merchant_payment_id: str
    amount: Decimal
    currency: str
    description: str
    return_url: str
    callback_url: str


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    provider_reference: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    event_id: str
    provider_reference: str
    merchant_payment_id: str
    succeeded: bool
    amount: Decimal
    currency: str
    occurred_at: datetime
    failure_reason: str | None = None


class PaymentGatewayError(Exception):
    """The gateway could not be reached or refused the request."""


class InvalidCallbackError(PaymentGatewayError):
    """A callback failed signature or payload validation (NFR-11)."""


class PaymentGateway(ABC):
    name: str

    @abstractmethod
    async def create_checkout(self, request: CheckoutRequest) -> CheckoutSession: ...

    @abstractmethod
    def parse_callback(self, body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        """Verify and decode a gateway callback. Raises InvalidCallbackError."""

    @abstractmethod
    async def refund(self, provider_reference: str, amount: Decimal) -> str:
        """Refund a captured payment; returns the provider's refund reference."""

    async def aclose(self) -> None:
        return None
