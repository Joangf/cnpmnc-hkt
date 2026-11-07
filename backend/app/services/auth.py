"""Registration, login, password reset (FRD 4.1)."""

import asyncio
import hmac
import secrets
from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    Conflict,
    EmailDeliveryFailed,
    Forbidden,
    TooManyRequests,
    Unauthorized,
    ValidationFailed,
)
from app.core.security import generate_token, hash_password, sha256_hex, verify_password
from app.models import PatientProfile, User
from app.models.enums import AccountStatus, UserRole
from app.repositories import users as user_repo
from app.schemas.auth import RegisterRequest
from app.services import audit, email

logger = structlog.get_logger(__name__)

# Verified against when the email is unknown, so response time does not reveal accounts.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def _otp_digest(address: str, otp: str) -> str:
    return sha256_hex(f"{address}:{otp}")


async def _issue_registration_otp(redis: Redis, user: User) -> str | None:
    """Email a fresh OTP. Returns the code only when no email provider is set up in dev."""
    if not email.is_configured() and not settings.is_dev:
        raise EmailDeliveryFailed()
    if not await redis.set(
        f"regotp:cooldown:{user.id}", "1", nx=True, ex=settings.otp_resend_cooldown_seconds
    ):
        raise TooManyRequests("Please wait a minute before requesting another code.")

    otp = f"{secrets.randbelow(10**6):06d}"
    await redis.set(f"regotp:{user.id}", _otp_digest(user.email, otp), ex=settings.otp_ttl_seconds)
    await redis.delete(f"regotp:attempts:{user.id}")

    if not email.is_configured():
        logger.warning("registration.otp_not_emailed", user_id=user.id, reason="no RESEND_API_KEY")
        return otp
    try:
        name = user.profile.full_name if user.profile else "there"
        await email.send_registration_otp(user.email, name, otp)
    except EmailDeliveryFailed:
        await redis.delete(f"regotp:{user.id}", f"regotp:cooldown:{user.id}")
        raise
    return None


async def register(session: AsyncSession, redis: Redis, payload: RegisterRequest) -> str | None:
    """Create (or refresh) an unverified account and email its OTP.

    Returns the OTP only in dev when no email provider is configured; otherwise None.
    """
    address = payload.email.lower()
    password_hash = await asyncio.to_thread(hash_password, payload.password)
    user = await user_repo.get_by_email(session, address)
    if user is not None and user.account_status != AccountStatus.PENDING:
        raise Conflict("An account with this email already exists.", code="EmailTaken")

    if user is not None:
        # Abandoned, unverified registration: let the real owner of the address start over.
        user.password_hash = password_hash
        profile = user.profile or PatientProfile()
        profile.full_name = payload.full_name
        profile.date_of_birth = payload.date_of_birth
        profile.phone_number = payload.phone_number
        user.profile = profile
    else:
        user = User(
            email=address,
            password_hash=password_hash,
            role=UserRole.PATIENT,
            account_status=AccountStatus.PENDING,
        )
        user.profile = PatientProfile(
            full_name=payload.full_name,
            date_of_birth=payload.date_of_birth,
            phone_number=payload.phone_number,
        )
        session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict("An account with this email already exists.", code="EmailTaken") from exc
    audit.record(session, "user.registration_started", "user", user.id, actor_id=user.id)
    await session.commit()
    return await _issue_registration_otp(redis, user)


async def resend_registration_otp(session: AsyncSession, redis: Redis, address: str) -> str | None:
    """Silent for unknown or already-verified emails so the endpoint reveals nothing."""
    user = await user_repo.get_by_email(session, address.lower())
    if user is None or user.account_status != AccountStatus.PENDING:
        return None
    return await _issue_registration_otp(redis, user)


async def verify_registration(session: AsyncSession, redis: Redis, address: str, otp: str) -> User:
    invalid = ValidationFailed("That code is incorrect or has expired.", code="InvalidOtp")
    user = await user_repo.get_by_email(session, address.lower())
    if user is None or user.account_status != AccountStatus.PENDING:
        raise invalid

    attempts = await redis.incr(f"regotp:attempts:{user.id}")
    if attempts == 1:
        await redis.expire(f"regotp:attempts:{user.id}", settings.otp_ttl_seconds)
    if attempts > settings.otp_max_attempts:
        await redis.delete(f"regotp:{user.id}")  # force a new code after too many guesses
        raise TooManyRequests("Too many incorrect codes. Please request a new one.")

    stored = await redis.get(f"regotp:{user.id}")
    if not stored or not hmac.compare_digest(stored, _otp_digest(user.email, otp)):
        raise invalid

    user.account_status = AccountStatus.ACTIVE
    audit.record(session, "user.registered", "user", user.id, actor_id=user.id)
    await session.commit()
    await redis.delete(
        f"regotp:{user.id}", f"regotp:attempts:{user.id}", f"regotp:cooldown:{user.id}"
    )
    return user


async def login(
    session: AsyncSession, redis: Redis, email: str, password: str, client_ip: str
) -> User:
    email = email.lower()
    key = f"ratelimit:login:{client_ip}:{sha256_hex(email)}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, settings.login_rate_window_seconds)
    if attempts > settings.login_rate_limit:
        raise TooManyRequests("Too many login attempts. Please try again later.")

    user = await user_repo.get_by_email(session, email)
    valid = await asyncio.to_thread(
        verify_password, password, user.password_hash if user else _DUMMY_HASH
    )
    if user is None or not valid:
        raise Unauthorized("Invalid email or password.", code="InvalidCredentials")
    if user.account_status == AccountStatus.PENDING:
        raise Forbidden(
            "Your email is not verified yet. Register again with the same email to get a new code.",
            code="AccountNotVerified",
        )
    if user.account_status != AccountStatus.ACTIVE:
        raise Forbidden("This account has been deactivated.", code="AccountInactive")

    await redis.delete(key)
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user


async def request_password_reset(session: AsyncSession, redis: Redis, email: str) -> str | None:
    """Returns the raw token (callers only expose it in dev). Silent for unknown emails."""
    user = await user_repo.get_by_email(session, email)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        return None
    token = generate_token()
    await redis.set(
        f"pwreset:{sha256_hex(token)}", str(user.id), ex=settings.password_reset_ttl_seconds
    )
    audit.record(session, "user.password_reset_requested", "user", user.id, actor_id=user.id)
    await session.commit()
    return token


async def confirm_password_reset(
    session: AsyncSession, redis: Redis, token: str, new_password: str
) -> None:
    key = f"pwreset:{sha256_hex(token)}"
    user_id = await redis.get(key)
    if not user_id:
        raise ValidationFailed(
            "This reset link is invalid or has expired.", code="InvalidResetToken"
        )
    user = await user_repo.get_by_id(session, int(user_id))
    if user is None:
        raise ValidationFailed(
            "This reset link is invalid or has expired.", code="InvalidResetToken"
        )
    user.password_hash = await asyncio.to_thread(hash_password, new_password)
    audit.record(session, "user.password_reset", "user", user.id, actor_id=user.id)
    await session.commit()
    await redis.delete(key)
