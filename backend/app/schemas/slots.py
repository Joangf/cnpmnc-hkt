from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.schemas.admin import Capacity, ScopeId
from app.schemas.common import ORMModel


class SlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: AwareDatetime
    end_time: AwareDatetime
    capacity: Capacity = 1
    is_open: bool = Field(default=True, strict=True)


class SlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: ScopeId
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None
    capacity: Capacity | None = None
    is_open: bool | None = Field(default=None, strict=True)

    @field_validator("start_time", "end_time", "capacity", "is_open")
    @classmethod
    def cannot_clear(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("Slot fields cannot be empty.")
        return value


class AdminSlotOut(ORMModel):
    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    capacity: int
    is_open: bool
    version: int
    booked_count: int
    remaining_places: int


class AdminSlotList(BaseModel):
    synced_at: datetime | None = None
    doctor_id: int
    timezone: str
    slots: list[AdminSlotOut]
