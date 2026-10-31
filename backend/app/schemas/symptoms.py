from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

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


class RecommendationResponse(BaseModel):
    matched_symptoms: list[SymptomOut]
    specialties: list[SpecialtyRecommendation]
    departments: list[RecommendedDepartment]
    urgent_warning: str | None
    disclaimer: str
