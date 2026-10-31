"""Pure slot generation for the hybrid scheduling model (FRD 4.4.1).

1. Candidate start times are generated every `increment` from each window start.
2. A candidate is offered only if duration + buffer fits fully inside the window.
3. Candidates overlapping existing bookings (incl. their buffer) or blocked periods are dropped.
4. Windows that already reached `max_appointments` offer nothing.

No I/O, so it is trivially unit-testable (see tests/test_scheduling.py).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Interval:
    start: datetime
    end: datetime

    def overlaps(self, other: "Interval") -> bool:
        # Half-open [start, end), same semantics as Postgres tstzrange default '[)'.
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True, slots=True)
class ScheduleWindow:
    start: datetime
    end: datetime
    max_appointments: int | None = None


@dataclass(frozen=True, slots=True)
class Slot:
    start: datetime
    end: datetime  # end of the consultation itself (buffer excluded)


def generate_slots(
    windows: Iterable[ScheduleWindow],
    busy: Iterable[Interval],
    *,
    duration: timedelta,
    buffer: timedelta = timedelta(0),
    increment: timedelta,
    blocked: Iterable[Interval] = (),
    not_before: datetime | None = None,
) -> list[Slot]:
    if duration <= timedelta(0):
        raise ValueError("duration must be positive")
    if increment <= timedelta(0):
        raise ValueError("increment must be positive")
    if buffer < timedelta(0):
        raise ValueError("buffer must not be negative")

    busy_list = list(busy)
    unavailable = busy_list + list(blocked)
    slots: list[Slot] = []

    for window in sorted(windows, key=lambda w: w.start):
        if window.max_appointments is not None:
            booked = sum(1 for b in busy_list if window.start <= b.start < window.end)
            if booked >= window.max_appointments:
                continue

        candidate = window.start
        while candidate + duration + buffer <= window.end:
            reserved = Interval(candidate, candidate + duration + buffer)
            if (not_before is None or candidate >= not_before) and not any(
                reserved.overlaps(u) for u in unavailable
            ):
                slots.append(Slot(candidate, candidate + duration))
            candidate += increment

    return slots
