"""Slot generation, including the illustrative example from FRD 4.4.1."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.scheduling import Interval, ScheduleWindow, generate_slots

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
TEN = timedelta(minutes=10)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 2, hour, minute, tzinfo=TZ)


WINDOW = [ScheduleWindow(at(7), at(8))]


def starts(slots: list) -> list[datetime]:
    return [s.start for s in slots]


def test_frd_example_type_a_20_minutes_with_buffer() -> None:
    slots = generate_slots(WINDOW, [], duration=timedelta(minutes=20), buffer=TEN, increment=TEN)
    assert starts(slots) == [at(7, 0), at(7, 10), at(7, 20), at(7, 30)]
    assert slots[0].end == at(7, 20)  # buffer is reserved but not part of the consultation


def test_frd_example_type_b_30_minutes_with_buffer() -> None:
    slots = generate_slots(WINDOW, [], duration=timedelta(minutes=30), buffer=TEN, increment=TEN)
    assert starts(slots) == [at(7, 0), at(7, 10), at(7, 20)]


def test_existing_booking_and_its_buffer_block_overlapping_candidates() -> None:
    busy = [Interval(at(7, 0), at(7, 30))]  # 20 min + 10 min buffer
    slots = generate_slots(WINDOW, busy, duration=timedelta(minutes=20), buffer=TEN, increment=TEN)
    assert starts(slots) == [at(7, 30)]


def test_blocked_period_is_excluded() -> None:
    blocked = [Interval(at(7, 40), at(8, 0))]
    slots = generate_slots(
        WINDOW, [], blocked=blocked, duration=timedelta(minutes=20), buffer=TEN, increment=TEN
    )
    assert starts(slots) == [at(7, 0), at(7, 10)]


def test_not_before_drops_candidates_in_the_past() -> None:
    slots = generate_slots(
        WINDOW, [], duration=timedelta(minutes=20), buffer=TEN, increment=TEN, not_before=at(7, 15)
    )
    assert starts(slots) == [at(7, 20), at(7, 30)]


def test_capacity_limit_closes_window() -> None:
    window = [ScheduleWindow(at(7), at(8), max_appointments=1)]
    busy = [Interval(at(7, 0), at(7, 30))]
    assert (
        generate_slots(window, busy, duration=timedelta(minutes=20), buffer=TEN, increment=TEN)
        == []
    )


def test_multiple_windows_are_sorted() -> None:
    windows = [ScheduleWindow(at(13), at(13, 30)), ScheduleWindow(at(8), at(8, 30))]
    slots = generate_slots(windows, [], duration=timedelta(minutes=20), increment=TEN)
    assert starts(slots) == [at(8, 0), at(8, 10), at(13, 0), at(13, 10)]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"duration": timedelta(0), "increment": TEN},
        {"duration": TEN, "increment": timedelta(0)},
        {"duration": TEN, "increment": TEN, "buffer": timedelta(minutes=-1)},
    ],
)
def test_invalid_configuration_raises(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        generate_slots(WINDOW, [], **kwargs)


# --- Interval boundaries (SCRUM-24 AC-6) ------------------------------------------------------
# Window 07:00-09:00, existing booking reserves [07:30, 08:00) (20 min + 10 min buffer).
BOUNDARY_WINDOW = [ScheduleWindow(at(7), at(9))]
BOOKED = [Interval(at(7, 30), at(8, 0))]


@pytest.mark.parametrize(
    ("candidate", "offered", "case"),
    [
        (at(7, 0), True, "ends exactly where the booking starts (adjacent before)"),
        (at(8, 0), True, "starts exactly where the booking's buffer ends (adjacent after)"),
        (at(7, 10), False, "own buffer runs into the booking (partial overlap)"),
        (at(7, 30), False, "identical start time"),
        (at(7, 50), False, "starts inside the booking's buffer"),
        (at(8, 30), True, "duration + buffer ends exactly at the window end"),
        (at(8, 40), False, "duration + buffer would run past the window end"),
    ],
)
def test_interval_boundaries_are_half_open(candidate: datetime, offered: bool, case: str) -> None:
    slots = generate_slots(
        BOUNDARY_WINDOW, BOOKED, duration=timedelta(minutes=20), buffer=TEN, increment=TEN
    )
    assert (candidate in starts(slots)) is offered, case


def test_multi_slot_appointment_needs_its_whole_interval_free() -> None:
    # A 60-minute consultation spans six 10-minute increments; any overlap disqualifies it.
    slots = generate_slots(BOUNDARY_WINDOW, BOOKED, duration=timedelta(minutes=60), increment=TEN)
    assert starts(slots) == [at(8, 0)]


def test_capacity_counts_existing_bookings_up_to_the_configured_limit() -> None:
    window = [ScheduleWindow(at(7), at(9), max_appointments=2)]
    one = [Interval(at(7, 0), at(7, 30))]
    two = one + [Interval(at(8, 0), at(8, 30))]
    within = generate_slots(window, one, duration=timedelta(minutes=20), buffer=TEN, increment=TEN)
    assert within, "a window under its limit keeps offering non-overlapping slots"
    assert (
        generate_slots(window, two, duration=timedelta(minutes=20), buffer=TEN, increment=TEN) == []
    )
