from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AccountStatus, UserRole
from app.schemas.validators import DateOfBirth, FullName, Password, PhoneNumber


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    full_name: FullName
    date_of_birth: DateOfBirth
    phone_number: PhoneNumber


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserMe(BaseModel):
    id: int
    email: str
    role: UserRole
    account_status: AccountStatus
    full_name: str | None
    patient_id: int | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserMe


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequested(BaseModel):
    message: str
    # Only populated when ENV=dev, because no email channel exists yet (FR-NOT-04).
    dev_reset_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: Password
