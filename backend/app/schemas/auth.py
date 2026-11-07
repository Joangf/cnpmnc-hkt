from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AccountStatus, UserRole
from app.schemas.validators import FullName, OptionalDateOfBirth, OptionalPhoneNumber, Password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    full_name: FullName
    date_of_birth: OptionalDateOfBirth = None
    phone_number: OptionalPhoneNumber = None


class RegistrationPending(BaseModel):
    email: str
    message: str
    expires_in: int
    # Only populated when ENV=dev and no email provider is configured (RESEND_API_KEY unset).
    dev_otp: str | None = None


class VerifyRegistrationRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ResendOtpRequest(BaseModel):
    email: EmailStr


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
