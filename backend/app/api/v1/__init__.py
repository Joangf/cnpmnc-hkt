from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_slots,
    appointments,
    auth,
    availability,
    directory,
    integrations,
    notifications,
    payments,
    profile,
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
    reviews,
    notifications,
    integrations,
    admin,
    admin_slots,
):
    api_router.include_router(module.router)
