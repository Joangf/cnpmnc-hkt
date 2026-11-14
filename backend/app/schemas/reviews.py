from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import ReviewStatus
from app.schemas.common import ORMModel
from app.schemas.validators import ShortText


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class ReviewUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class ReviewOut(ORMModel):
    id: int
    appointment_id: int
    doctor_id: int
    rating: int
    comment: str | None
    status: ReviewStatus
    is_edited: bool = False
    created_at: datetime


class ReviewPublic(BaseModel):
    id: int
    rating: int
    comment: str | None
    # Reviewer identity is not exposed publicly (NFR-04).
    author: str = "Verified patient"
    is_edited: bool = False
    created_at: datetime


class AdminReviewOut(ReviewOut):
    doctor_name: str
    patient_id: int
    moderation_note: str | None
    open_reports: int = 0  # SCRUM-50: patient reports waiting for a decision
    report_reasons: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True, json_schema_serialization_defaults_required=True
    )


class ReportCreate(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    details: ShortText | None = None


class ReportOut(BaseModel):
    id: int
    review_id: int
    reason: str
    status: str
    created_at: datetime
    already_reported: bool  # True: this patient's earlier open report was returned


class ReviewModerate(BaseModel):
    status: Literal["PUBLISHED", "HIDDEN", "REMOVED"]
    note: ShortText | None = None


class ReviewSummaryPoint(BaseModel):
    text: str
    review_ids: list[int]  # the published reviews this point comes from


class ReviewSummaryOut(BaseModel):
    """AI summary of a doctor's published reviews (SCRUM-46).

    status: ready | insufficient (fewer than `min_reviews` commented reviews) |
    generating (another request is writing it) | unavailable (AI off or failing).
    """

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    status: Literal["ready", "insufficient", "generating", "unavailable"]
    summary: str | None = None
    points: list[ReviewSummaryPoint] = Field(default_factory=list)
    review_count: int
    min_reviews: int
    generated_at: datetime | None = None
    stale: bool = False
