from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, SessionDep
from app.schemas.common import error_responses
from app.schemas.notifications import NotificationList, NotificationOut
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationList,
    operation_id="listNotifications",
    responses=error_responses(401),
)
async def list_notifications(
    user: CurrentUser,
    session: SessionDep,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> NotificationList:
    items, unread = await notification_service.list_for_user(
        session, user.id, unread_only=unread_only, limit=limit
    )
    return NotificationList(
        items=[NotificationOut.model_validate(n) for n in items], unread_count=unread
    )


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="markAllNotificationsRead",
    responses=error_responses(401),
)
async def mark_all_read(user: CurrentUser, session: SessionDep) -> Response:
    await notification_service.mark_all_read(session, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    operation_id="markNotificationRead",
    responses=error_responses(401, 404),
)
async def mark_read(
    notification_id: int, user: CurrentUser, session: SessionDep
) -> NotificationOut:
    return NotificationOut.model_validate(
        await notification_service.mark_read(session, user.id, notification_id)
    )
