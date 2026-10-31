from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.models.enums import ReviewStatus
from app.schemas.common import ORMModel
from app.schemas.validators import ShortText


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class ReviewOut(ORMModel):
    id: int
    appointment_id: int
    doctor_id: int
    rating: int
    comment: str | None
    status: ReviewStatus
    created_at: datetime


class ReviewPublic(BaseModel):
    id: int
    rating: int
    comment: str | None
    # Reviewer identity is not exposed publicly (NFR-04).
    author: str = "Verified patient"
    created_at: datetime


class AdminReviewOut(ReviewOut):
    doctor_name: str
    patient_id: int
    moderation_note: str | None


class ReviewModerate(BaseModel):
    status: Literal["PUBLISHED", "HIDDEN", "REMOVED"]
    note: ShortText | None = None
