"""SePay / VietQR helpers. Plain functions, no adapter layer (docs/sprint3-sepay-plan.md D1-D5).

QR URL builders (used by the presenters), payment codes, webhook auth and the User API
transaction fetch.
"""

import hmac
import re
import secrets
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx

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


# --- Incoming transfers (D3, D5) -----------------------------------------------------------

# SePay reports transaction times as Vietnam local time without an offset.
SEPAY_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 8


@dataclass(frozen=True)
class BankTransfer:
    """One incoming bank transaction, from the webhook or the User API."""

    id: str
    amount_in: Decimal
    transaction_content: str
    code: str | None
    transaction_date: datetime


def new_payment_code() -> str:
    """`PREFIX` + 8 random [A-Z0-9]; the transfer content the patient must send (D3)."""
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))
    return f"{settings.payment_code_prefix}{suffix}"


def extract_codes(code: str | None, content: str | None) -> list[str]:
    """Candidate payment codes in a transfer, best first.

    SePay's own `code` field wins. Otherwise scan the content upper-cased with whitespace
    removed (banks insert spaces and prefixes); overlapping matches are all returned so a
    bank prefix such as "OCB" in front of the code cannot hide it.
    """
    prefix = re.escape(settings.payment_code_prefix)
    pattern = re.compile(f"(?=({prefix}[A-Z0-9]{{{_CODE_LENGTH}}}))")
    found: list[str] = []
    for text in (code, content):
        normalized = re.sub(r"\s+", "", text or "").upper()
        for match in pattern.finditer(normalized):
            if match.group(1) not in found:
                found.append(match.group(1))
    return found


def check_api_key(authorization: str | None) -> bool:
    """SePay webhook auth: `Authorization: Apikey <key>`. An unset key rejects every call."""
    expected = settings.sepay_webhook_api_key
    if not expected or not authorization:
        return False
    scheme, _, value = authorization.strip().partition(" ")
    return scheme.lower() == "apikey" and hmac.compare_digest(
        value.strip().encode(), expected.encode()
    )


def parse_local_time(value: str | None) -> datetime:
    """'YYYY-MM-DD HH:MM:SS' in Vietnam time -> aware UTC; now if missing or malformed."""
    try:
        parsed = datetime.strptime(value or "", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now(UTC)
    return parsed.replace(tzinfo=SEPAY_TZ).astimezone(UTC)


async def fetch_transactions(since: datetime) -> list[BankTransfer]:
    """Incoming transactions since `since` from the SePay User API (D5 polling path).

    Raises httpx.HTTPError on network/HTTP failure; the caller treats that as a failed run.
    """
    params: dict[str, str | int] = {
        "transaction_date_min": since.astimezone(SEPAY_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "limit": 200,
    }
    async with httpx.AsyncClient(timeout=settings.sepay_timeout_seconds) as client:
        response = await client.get(
            f"{settings.sepay_api_base.rstrip('/')}/transactions/list",
            params=params,
            headers={"Authorization": f"Bearer {settings.sepay_api_token}"},
        )
        response.raise_for_status()
    transfers = []
    for row in response.json().get("transactions") or []:
        amount = Decimal(str(row.get("amount_in") or "0"))
        if amount <= 0:
            continue
        transfers.append(
            BankTransfer(
                id=str(row["id"]),
                amount_in=amount,
                transaction_content=row.get("transaction_content") or "",
                code=row.get("code"),
                transaction_date=parse_local_time(row.get("transaction_date")),
            )
        )
    return transfers
