from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PaymentStatus


class PaymentInitResponse(BaseModel):
    payment_id: int
    status: PaymentStatus
    amount: Decimal
    currency: str
    checkout_url: str


class PaymentOut(BaseModel):
    id: int
    appointment_id: int
    booking_reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    provider_reference: str | None
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime
