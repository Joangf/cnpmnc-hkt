"""Reusable field validators (FR-PRO-03). Mirrored by the zod schemas in the frontend."""

import re
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, StringConstraints

_PHONE_RE = re.compile(r"^\+?[0-9]{9,15}$")


def _phone(value: str) -> str:
    cleaned = re.sub(r"[\s\-().]", "", value)
    if not _PHONE_RE.fullmatch(cleaned):
        raise ValueError("Phone number must contain 9-15 digits and may start with +.")
    return cleaned


def _date_of_birth(value: date) -> date:
    today = date.today()
    if value >= today:
        raise ValueError("Date of birth must be in the past.")
    if value.year < today.year - 130:
        raise ValueError("Date of birth is not plausible.")
    return value


def _password(value: str) -> str:
    if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
        raise ValueError("Password must contain at least one letter and one digit.")
    return value


PhoneNumber = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=25), AfterValidator(_phone)
]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
DateOfBirth = Annotated[date, AfterValidator(_date_of_birth)]
Password = Annotated[
    str, StringConstraints(min_length=8, max_length=128), AfterValidator(_password)
]


def _blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


# Optional form fields: an empty string means "not provided".
OptionalDateOfBirth = Annotated[DateOfBirth | None, BeforeValidator(_blank_to_none)]
OptionalPhoneNumber = Annotated[PhoneNumber | None, BeforeValidator(_blank_to_none)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]


def bounded(max_length: int, min_length: int = 0) -> StringConstraints:
    """Stripped-string bounds matching a column's length, so oversize input is a 422."""
    return StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)
