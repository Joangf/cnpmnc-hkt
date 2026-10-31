"""Registration, login, password reset (FRD 4.1)."""

import asyncio
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import Conflict, Forbidden, TooManyRequests, Unauthorized, ValidationFailed
from app.core.security import generate_token, hash_password, sha256_hex, verify_password
from app.models import PatientProfile, User
from app.models.enums import AccountStatus, UserRole
from app.repositories import users as user_repo
from app.schemas.auth import RegisterRequest
from app.services import audit

# Verified against when the email is unknown, so response time does not reveal accounts.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


async def register(session: AsyncSession, payload: RegisterRequest) -> User:
    email = payload.email.lower()
    if await user_repo.get_by_email(session, email):
        raise Conflict("An account with this email already exists.", code="EmailTaken")

    user = User(
        email=email,
        # Argon2 is CPU-bound; keep it off the event loop.
        password_hash=await asyncio.to_thread(hash_password, payload.password),
        role=UserRole.PATIENT,
        account_status=AccountStatus.ACTIVE,
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
    audit.record(session, "user.registered", "user", user.id, actor_id=user.id)
    await session.commit()
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
