from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class ErpEvent(BaseModel):
    """Status push from the hospital ERP/HIS (FRD 5.4). Signed with X-Erp-Timestamp /
    X-Erp-Signature = hex(HMAC-SHA256(secret, "{timestamp}.{body}"))."""

    event_id: str = Field(min_length=1, max_length=64)
    type: Literal[
        "APPOINTMENT_STATUS_CHANGED", "CHECK_IN_STATUS_CHANGED", "APPOINTMENT_RESCHEDULED"
    ]
    booking_reference: str = Field(min_length=1, max_length=16)
    erp_booking_id: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    check_in_status: str | None = Field(default=None, max_length=32)
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None
    reason: str | None = Field(default=None, max_length=500)
    occurred_at: AwareDatetime


class WebhookAck(BaseModel):
    status: Literal["processed", "ignored", "duplicate"]
