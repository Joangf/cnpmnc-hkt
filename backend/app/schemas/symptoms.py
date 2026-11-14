from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.common import ORMModel


class SymptomOut(ORMModel):
    id: int
    name: str
    description: str | None


class RecommendationRequest(BaseModel):
    symptom_ids: list[int] = Field(default_factory=list, max_length=20)
    free_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = (
        None
    )
    # AI flow: the patient's own words, used ONLY to rank doctors and word the explanation -
    # never to add symptoms (the patient already confirmed `symptom_ids`).
    context_text: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None
    explain: bool = False  # ask the AI to explain the ranking (cached per symptom set)

    @model_validator(mode="after")
    def _has_input(self) -> "RecommendationRequest":
        if not self.symptom_ids and not self.free_text:
            raise ValueError("Select at least one symptom or describe your symptoms.")
        return self


class SpecialtyRecommendation(BaseModel):
    specialty_id: int
    name: str
    score: float
    matched_symptoms: list[str]


class RecommendedDepartment(BaseModel):
    department_id: int
    department_name: str
    hospital_id: int
    hospital_name: str
    city: str
    specialty_id: int


class TraceStep(BaseModel):
    """One step of the AI pipeline, shown in the "How we got this" panel."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    key: str
    title: str
    summary: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    skipped: bool = False


class DoctorRecommendation(BaseModel):
    doctor_id: int
    full_name: str
    title: str | None
    specialty_id: int
    department_id: int
    department_name: str
    hospital_id: int
    hospital_name: str
    rating_avg: float
    rating_count: int
    next_available: datetime | None
    score: float
    score_relevance: float | None  # None when no text was given or AI is off
    score_rating: float
    score_availability: float


class SpecialtyExplanation(BaseModel):
    specialty_id: int
    reason: str


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
    matched_symptoms: list[SymptomOut]
    specialties: list[SpecialtyRecommendation]
    departments: list[RecommendedDepartment]
    urgent_warning: str | None
    disclaimer: str
    mode: Literal["rules", "ai", "rule_fallback"] = "rules"
    doctors: list[DoctorRecommendation] = Field(default_factory=list)
    explanation: str | None = None
    specialty_explanations: list[SpecialtyExplanation] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)


class InterpretRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]


class InterpretedSymptom(BaseModel):
    id: int
    name: str
    score: float | None  # ColBERT match score; None in rule-only fallback
    matched_phrase: str | None
    via: Literal["text", "rephrase", "rules"]


class InterpretResponse(BaseModel):
    mode: Literal["ai", "rule_fallback"]
    symptoms: list[InterpretedSymptom]
    urgent_warning: str | None
    disclaimer: str
    trace: list[TraceStep]


# --- admin: symptom catalog and rules (SCRUM-43) ----------------------------------------------

_Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
_Keywords = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
_Message = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class AdminRuleOut(BaseModel):
    id: int
    symptom_id: int
    specialty_id: int
    specialty_name: str
    weight: float
    is_active: bool


class AdminSymptomOut(BaseModel):
    id: int
    name: str
    keywords: str | None  # comma-separated synonyms, any language; used by the AI search
    description: str | None
    is_red_flag: bool
    red_flag_message: str | None
    is_active: bool
    rules: list[AdminRuleOut]


class AdminSymptomCreate(BaseModel):
    name: _Name
    keywords: _Keywords | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None
    ) = None
    is_red_flag: bool = False
    red_flag_message: _Message | None = None
    is_active: bool = True


class AdminSymptomUpdate(BaseModel):
    name: _Name | None = None
    keywords: _Keywords | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None
    ) = None
    is_red_flag: bool | None = None
    red_flag_message: _Message | None = None
    is_active: bool | None = None


class AdminRuleCreate(BaseModel):
    specialty_id: int
    weight: float = Field(default=1.0, gt=0, le=5)


class AdminRuleUpdate(BaseModel):
    weight: float | None = Field(default=None, gt=0, le=5)
    is_active: bool | None = None
