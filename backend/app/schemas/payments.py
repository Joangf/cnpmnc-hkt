"""Payment / refund API contract (Sprint 3, docs/sprint3-sepay-plan.md section 3c). Frozen."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import PaymentStatus, RefundStatus
from app.schemas.validators import ShortText


class PaymentOut(BaseModel):
    id: int
    appointment_id: int
    booking_reference: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    # Bank-transfer instructions (FR-PAY-02): the QR encodes all of them.
    payment_code: str = Field(description="Transfer content; must appear in the bank transfer.")
    expires_at: datetime | None
    qr_image_url: str
    bank_code: str
    account_number: str
    account_name: str
    provider_reference: str | None = Field(description="SePay transaction id once settled.")
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime
    refund_status: RefundStatus | None
    refund_reference: str | None
    refund_bank_name: str | None
    refund_account_number: str | None
    refund_account_name: str | None
    refund_reason: str | None
    refund_note: str | None
    refund_requested_at: datetime | None
    refunded_at: datetime | None


class AdminRefundOut(PaymentOut):
    patient_name: str
    patient_email: str
    refund_qr_image_url: str | None = Field(
        description="VietQR image paying the refund to the patient's account (admin scans it)."
    )


AccountNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9A-Za-z]{4,32}$")
]
AccountName = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=2, max_length=128)
]


class RefundRequestIn(BaseModel):
    bank_bin: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{6}$")]
    bank_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=64)]
    account_number: AccountNumber
    account_name: AccountName
    reason: ShortText | None = None


class RefundCompleteIn(BaseModel):
    note: ShortText | None = Field(default=None, description="Bank transaction reference, if any.")


class RefundRejectIn(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class SepayWebhookIn(BaseModel):
    """SePay transaction webhook body (https://docs.sepay.vn/tich-hop-webhooks.html)."""

    model_config = ConfigDict(extra="ignore")

    id: int
    gateway: str | None = None
    transactionDate: str  # "YYYY-MM-DD HH:MM:SS", Vietnam local time
    accountNumber: str | None = None
    subAccount: str | None = None
    code: str | None = None
    content: str = ""
    transferType: Literal["in", "out"]
    transferAmount: Decimal
    accumulated: Decimal | None = None
    referenceCode: str | None = None
    description: str | None = None


class SepayWebhookAck(BaseModel):
    success: Literal[True] = True
