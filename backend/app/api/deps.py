from typing import Annotated

import structlog
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.redis import get_redis
from app.core.security import decode_token
from app.integrations.erp.base import ErpAdapter
from app.integrations.payment.base import PaymentGateway
from app.models import PatientProfile, User
from app.models.enums import AccountStatus, UserRole
from app.repositories import users as user_repo

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise Unauthorized()
    payload = decode_token(credentials.credentials, "access")
    user = await user_repo.get_by_id(session, int(payload["sub"]))
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise Unauthorized("Your session is no longer valid.", code="InvalidToken")
    # Picked up by RequestContextMiddleware for the access log (user id only, never PII).
    request.state.user_id = user.id
    structlog.contextvars.bind_contextvars(user_id=user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_patient(user: CurrentUser) -> PatientProfile:
    if user.role != UserRole.PATIENT or user.profile is None:
        raise Forbidden("A patient account is required.")
    return user.profile


CurrentPatient = Annotated[PatientProfile, Depends(get_current_patient)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:  # BR-13
        raise Forbidden("Administrator access is required.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_erp(request: Request) -> ErpAdapter:
    return request.app.state.erp  # type: ignore[no-any-return]


def get_payment_gateway(request: Request) -> PaymentGateway:
    return request.app.state.payment_gateway  # type: ignore[no-any-return]


ErpDep = Annotated[ErpAdapter, Depends(get_erp)]
GatewayDep = Annotated[PaymentGateway, Depends(get_payment_gateway)]


class PageParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size


PageDep = Annotated[PageParams, Depends()]


def client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )
