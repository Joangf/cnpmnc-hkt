from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request, Response, status
from redis.asyncio import Redis

from app.api import presenters
from app.api.deps import CurrentUser, RedisDep, SessionDep, client_ip
from app.core.config import settings
from app.core.errors import Unauthorized
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models import User
from app.models.enums import AccountStatus
from app.repositories import users as user_repo
from app.schemas.auth import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequested,
    RegisterRequest,
    RegistrationPending,
    ResendOtpRequest,
    TokenResponse,
    UserMe,
    VerifyRegistrationRequest,
)
from app.schemas.common import MessageResponse, error_responses
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_PATH = "/api/v1/auth"


def _issue_tokens(response: Response, user: User) -> TokenResponse:
    response.set_cookie(
        settings.refresh_cookie_name,
        create_refresh_token(user.id),
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=_COOKIE_PATH,
    )
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        expires_in=settings.access_token_minutes * 60,
        user=presenters.user_me(user),
    )


async def _revoke(redis: Redis, payload: dict[str, Any]) -> bool:
    """Mark a refresh token's jti as used. Returns False if it was already used/revoked."""
    ttl = max(int(payload["exp"] - datetime.now(UTC).timestamp()), 1)
    return bool(await redis.set(f"revoked:{payload['jti']}", "1", nx=True, ex=ttl))


def _pending(address: str, dev_otp: str | None) -> RegistrationPending:
    return RegistrationPending(
        email=address.lower(),
        message="If this email is awaiting verification, a 6-digit code has been sent to it.",
        expires_in=settings.otp_ttl_seconds,
        dev_otp=dev_otp,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegistrationPending,
    operation_id="register",
    responses=error_responses(409, 422, 429, 503),
)
async def register(
    payload: RegisterRequest, session: SessionDep, redis: RedisDep
) -> RegistrationPending:
    dev_otp = await auth_service.register(session, redis, payload)
    return _pending(payload.email, dev_otp)


@router.post(
    "/register/resend",
    response_model=RegistrationPending,
    operation_id="resendRegistrationOtp",
    responses=error_responses(422, 429, 503),
)
async def resend_registration_otp(
    payload: ResendOtpRequest, session: SessionDep, redis: RedisDep
) -> RegistrationPending:
    dev_otp = await auth_service.resend_registration_otp(session, redis, payload.email)
    return _pending(payload.email, dev_otp)


@router.post(
    "/register/verify",
    response_model=TokenResponse,
    operation_id="verifyRegistration",
    responses=error_responses(422, 429),
)
async def verify_registration(
    payload: VerifyRegistrationRequest, response: Response, session: SessionDep, redis: RedisDep
) -> TokenResponse:
    user = await auth_service.verify_registration(session, redis, payload.email, payload.otp)
    return _issue_tokens(response, user)


@router.post(
    "/login",
    response_model=TokenResponse,
    operation_id="login",
    responses=error_responses(401, 403, 422, 429),
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
) -> TokenResponse:
    user = await auth_service.login(
        session, redis, payload.email, payload.password, client_ip(request)
    )
    return _issue_tokens(response, user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    operation_id="refreshToken",
    responses=error_responses(401),
)
async def refresh(
    request: Request, response: Response, session: SessionDep, redis: RedisDep
) -> TokenResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise Unauthorized("No active session.", code="NoSession")
    payload = decode_token(token, "refresh")
    if not await _revoke(redis, payload):  # rotation: each refresh token works once
        raise Unauthorized("This session has expired. Please sign in again.", code="InvalidToken")
    user = await user_repo.get_by_id(session, int(payload["sub"]))
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise Unauthorized("This session has expired. Please sign in again.", code="InvalidToken")
    return _issue_tokens(response, user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="logout",
)
async def logout(request: Request, redis: RedisDep) -> Response:
    token = request.cookies.get(settings.refresh_cookie_name)
    if token:
        try:
            await _revoke(redis, decode_token(token, "refresh"))
        except Unauthorized:
            pass
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.refresh_cookie_name, path=_COOKIE_PATH)
    return response


@router.get(
    "/me", response_model=UserMe, operation_id="getCurrentUser", responses=error_responses(401)
)
async def me(user: CurrentUser) -> UserMe:
    return presenters.user_me(user)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequested,
    operation_id="requestPasswordReset",
    responses=error_responses(422),
)
async def request_password_reset(
    payload: PasswordResetRequest, session: SessionDep, redis: RedisDep
) -> PasswordResetRequested:
    token = await auth_service.request_password_reset(session, redis, payload.email)
    return PasswordResetRequested(
        message="If an account exists for this email, password reset instructions have been sent.",
        dev_reset_token=token if settings.is_dev else None,
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    operation_id="confirmPasswordReset",
    responses=error_responses(422),
)
async def confirm_password_reset(
    payload: PasswordResetConfirm, session: SessionDep, redis: RedisDep
) -> MessageResponse:
    await auth_service.confirm_password_reset(session, redis, payload.token, payload.new_password)
    return MessageResponse(message="Your password has been updated. You can now sign in.")
