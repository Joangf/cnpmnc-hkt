"""SePay / VietQR helpers. Plain functions, no adapter layer (docs/sprint3-sepay-plan.md D1-D5).

Phase 0 provides the QR URL builders used by the presenters. Session A adds the webhook
check, payment-code helpers and the User API transaction fetch here.
"""

from decimal import Decimal
from urllib.parse import urlencode

from app.core.config import settings


def payment_qr_url(amount: Decimal, payment_code: str) -> str:
    """VietQR image for paying `amount` into the SePay-monitored account (D4)."""
    query = urlencode(
        {
            "acc": settings.sepay_account,
            "bank": settings.sepay_bank,
            "amount": int(amount),
            "des": payment_code,
        }
    )
    return f"https://vietqr.app/img?{query}"


def refund_qr_url(
    bank_bin: str, account_number: str, account_name: str, amount: Decimal, reference: str
) -> str:
    """VietQR image the admin scans to pay a refund to the patient's account (D14)."""
    query = urlencode({"amount": int(amount), "addInfo": reference, "accountName": account_name})
    return f"https://img.vietqr.io/image/{bank_bin}-{account_number}-compact2.png?{query}"
