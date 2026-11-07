"""Transactional email through Resend (https://resend.com/docs/api-reference/emails/send-email)."""

from html import escape

import httpx
import structlog

from app.core.config import settings
from app.core.errors import EmailDeliveryFailed

logger = structlog.get_logger(__name__)

_RESEND_URL = "https://api.resend.com/emails"


class RecipientRestricted(EmailDeliveryFailed):
    """Resend refused the recipient (sandbox sender: only the account owner can be emailed)."""


def is_configured() -> bool:
    return bool(settings.resend_api_key)


async def send_email(to: str, subject: str, html: str, text: str) -> None:
    """Send one email. Raises EmailDeliveryFailed on any delivery problem."""
    try:
        async with httpx.AsyncClient(timeout=settings.email_timeout_seconds) as client:
            res = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
    except httpx.HTTPError as exc:
        logger.error("email.transport_error", error=str(exc))
        raise EmailDeliveryFailed() from exc
    if res.status_code >= 400:
        # Resend's error body never contains the message content, so it is safe to log.
        logger.error("email.rejected", status=res.status_code, body=res.text[:300])
        if res.status_code in (403, 422):  # sandbox: recipient not allowed
            raise RecipientRestricted()
        raise EmailDeliveryFailed()


async def send_registration_otp(to: str, full_name: str, otp: str) -> None:
    minutes = settings.otp_ttl_seconds // 60
    subject = f"{otp} is your verification code"
    text = (
        f"Hi {full_name},\n\nYour verification code is {otp}.\n"
        f"It expires in {minutes} minutes. If you did not create an account, ignore this email."
    )
    html = (
        f"<p>Hi {escape(full_name)},</p>"
        "<p>Use this code to confirm your registration:</p>"
        f'<p style="font-size:28px;font-weight:700;letter-spacing:6px">{otp}</p>'
        f"<p>It expires in {minutes} minutes. If you did not create an account, "
        "you can ignore this email.</p>"
    )
    await send_email(to, subject, html, text)
