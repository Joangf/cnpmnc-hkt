from datetime import date

from pydantic import BaseModel

from app.schemas.validators import DateOfBirth, FullName, PhoneNumber, ShortText


class ProfileOut(BaseModel):
    id: int
    email: str
    full_name: str
    date_of_birth: date | None
    phone_number: str | None
    address: str | None


class ProfileUpdate(BaseModel):
    full_name: FullName | None = None
    date_of_birth: DateOfBirth | None = None
    phone_number: PhoneNumber | None = None
    address: ShortText | None = None
