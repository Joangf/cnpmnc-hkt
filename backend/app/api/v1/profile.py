from fastapi import APIRouter

from app.api import presenters
from app.api.deps import CurrentPatient, CurrentUser, SessionDep
from app.core.errors import ValidationFailed
from app.schemas.common import error_responses
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import audit

router = APIRouter(prefix="/profile", tags=["profile"])

_REQUIRED = ("full_name",)  # date_of_birth and phone_number may be cleared


@router.get(
    "", response_model=ProfileOut, operation_id="getProfile", responses=error_responses(401, 403)
)
async def get_profile(user: CurrentUser, _patient: CurrentPatient) -> ProfileOut:
    return presenters.profile_out(user)


@router.patch(
    "",
    response_model=ProfileOut,
    operation_id="updateProfile",
    responses=error_responses(401, 403, 422),
)
async def update_profile(
    payload: ProfileUpdate, user: CurrentUser, patient: CurrentPatient, session: SessionDep
) -> ProfileOut:
    changes = payload.model_dump(exclude_unset=True)
    for field in _REQUIRED:
        if field in changes and changes[field] is None:
            raise ValidationFailed(f"'{field}' cannot be empty.")
    changed = [f for f, v in changes.items() if getattr(patient, f) != v]
    for field in changed:
        setattr(patient, field, changes[field])
    if changed:
        audit.record(
            session,
            "profile.updated",
            "patient_profile",
            patient.id,
            actor_id=user.id,
            details={"fields": sorted(changed)},  # field names only, no values (NFR-04)
        )
        await session.commit()
    return presenters.profile_out(user)
