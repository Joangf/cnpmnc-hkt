from fastapi import APIRouter

from app.api.v1 import (
    admin,
    appointments,
    auth,
    availability,
    directory,
    integrations,
    notifications,
    payments,
    profile,
    refunds,
    reviews,
    symptoms,
)

api_router = APIRouter()
for module in (
    auth,
    profile,
    directory,
    availability,
    symptoms,
    appointments,
    payments,
    refunds,
    reviews,
    notifications,
    integrations,
    admin,
):
    api_router.include_router(module.router)
