"""SCRUM-21 developer tests for scheduling input and effective settings."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.errors import ValidationFailed
from app.models import AppointmentType, Doctor
from app.schemas.admin import (
    AppointmentTypeCreate,
    AppointmentTypeUpdate,
    DoctorCreate,
    DoctorUpdate,
)
from app.services.scheduling import Interval, ScheduleWindow, generate_slots
from app.services.scheduling_settings import resolve


@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, 2.0, "2", 2147483648, None])
def test_capacity_rejects_invalid_values(value: object) -> None:
    for schema, body in (
        (DoctorCreate, {"full_name": "Doctor", "department_id": 1}),
        (DoctorUpdate, {}),
    ):
        with pytest.raises(ValidationError):
            schema.model_validate({**body, "max_appointments_per_window": value})


@pytest.mark.parametrize(
    "field,values",
    [
        ("duration_minutes", [0, 4, 481, True, 5.5, 20.0, "20", None]),
        ("buffer_minutes", [-1, 121, False, 0.5, 10.0, "10", None]),
        ("doctor_id", [0, -1, True, 1.5, "1"]),
        ("specialty_id", [0, -1, False, 1.5, "1"]),
    ],
)
def test_appointment_type_rejects_invalid_values(field: str, values: list[object]) -> None:
    for value in values:
        with pytest.raises(ValidationError):
            AppointmentTypeCreate.model_validate({
                "name": "Standard", "duration_minutes": 20, field: value,
            })
        with pytest.raises(ValidationError):
            AppointmentTypeUpdate.model_validate({field: value})


@pytest.mark.parametrize("duration,buffer", [(5, 0), (480, 120), (20, 10)])
def test_timing_boundaries_and_omitted_patch(duration: int, buffer: int) -> None:
    result = AppointmentTypeCreate(
        name="Standard", duration_minutes=duration, buffer_minutes=buffer
    )
    assert (result.duration_minutes, result.buffer_minutes) == (duration, buffer)
    assert AppointmentTypeUpdate().model_dump(exclude_unset=True) == {}
    assert DoctorUpdate().model_dump(exclude_unset=True) == {}
    assert DoctorCreate(full_name="Doctor", department_id=1).max_appointments_per_window == 1


def rules(capacity: int | None = 3):
    doctor = Doctor(id=1, max_appointments_per_window=capacity)
    appointment_type = AppointmentType(id=1, duration_minutes=20, buffer_minutes=10)
    return doctor, appointment_type, resolve(doctor, appointment_type)


@pytest.mark.parametrize("erp,expected", [(None, 3), (8, 3), (2, 2), (0, 0), (-1, 0), (True, 0)])
def test_stricter_erp_capacity_or_fail_closed(erp: int | None, expected: int) -> None:
    assert rules()[2].window_capacity(erp) == expected


def test_missing_capacity_is_finite_and_invalid_local_rules_are_rejected() -> None:
    assert rules(None)[2].window_capacity(None) == 1
    with pytest.raises(ValidationFailed):
        rules(0)


def test_settings_fingerprint_changes_with_timing_capacity_or_persisted_revision() -> None:
    doctor, appointment_type, old = rules()
    for field, value in [("duration_minutes", 30), ("buffer_minutes", 0)]:
        setattr(appointment_type, field, value)
        new = resolve(doctor, appointment_type)
        assert new.fingerprint != old.fingerprint
        old = new
    doctor.max_appointments_per_window = 1
    assert resolve(doctor, appointment_type).fingerprint != old.fingerprint
    old = resolve(doctor, appointment_type)
    doctor.updated_at = datetime.now(UTC)
    assert resolve(doctor, appointment_type).fingerprint != old.fingerprint


def test_capacity_half_open_windows_and_cancelled_intervals_not_counted() -> None:
    start = datetime(2030, 1, 1, 8, tzinfo=UTC)
    hour, half = timedelta(hours=1), timedelta(minutes=30)
    windows = [ScheduleWindow(start, start + hour, 1),
               ScheduleWindow(start + hour, start + 2 * hour, 1)]
    busy = [Interval(start, start + half)]
    slots = generate_slots(windows, busy, duration=half, increment=half)
    assert [slot.start for slot in slots] == [start + hour, start + hour + half]
