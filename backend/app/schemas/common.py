from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str


class RefOut(BaseModel):
    id: int
    name: str


_ERROR_DESCRIPTIONS: dict[int, str] = {
    400: "Bad request",
    401: "Not authenticated (Unauthorized, InvalidToken, InvalidCredentials)",
    403: "Forbidden (Forbidden, AccountInactive)",
    404: "Resource not found (NotFound)",
    409: "Conflict (SlotTaken, SlotUnavailable, InvalidState, DuplicateReview, ...)",
    422: "Validation failed (ValidationFailed)",
    429: "Too many requests (TooManyRequests)",
    503: "External integration unavailable (ErpUnavailable, PaymentGatewayUnavailable)",
}


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses=` entries for the shared error contract."""
    return {
        code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[code]} for code in codes
    }
