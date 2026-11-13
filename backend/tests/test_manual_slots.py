"""Shared-slot input validation; ERP integration contracts are in test_erp_owned_slots."""
import pytest
from pydantic import ValidationError
from app.schemas.slots import SlotCreate, SlotUpdate

@pytest.mark.parametrize("field,value", [
    ("capacity", 0), ("capacity", True), ("capacity", 1.5), ("capacity", None),
    ("is_open", "yes"),
])
def test_slot_input_validation(field, value):
    body = {"start_time": "2030-01-01T08:00:00+07:00",
            "end_time": "2030-01-01T08:30:00+07:00", field: value}
    with pytest.raises(ValidationError):
        SlotCreate.model_validate(body)
    with pytest.raises(ValidationError):
        SlotUpdate.model_validate({"version": 1, field: value})

