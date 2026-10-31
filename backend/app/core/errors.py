"""Application errors. Each maps to a stable `code` in the JSON error contract (NFR-12)."""


class AppError(Exception):
    status_code: int = 400
    code: str = "BadRequest"
    message: str = "The request could not be processed."

    def __init__(self, message: str | None = None, code: str | None = None) -> None:
        if message:
            self.message = message
        if code:
            self.code = code
        super().__init__(self.message)


class Unauthorized(AppError):
    status_code = 401
    code = "Unauthorized"
    message = "Authentication is required."


class Forbidden(AppError):
    status_code = 403
    code = "Forbidden"
    message = "You do not have permission to perform this action."


class NotFound(AppError):
    status_code = 404
    code = "NotFound"
    message = "The requested resource was not found."


class Conflict(AppError):
    status_code = 409
    code = "Conflict"
    message = "The request conflicts with the current state of the resource."


class SlotTaken(Conflict):
    code = "SlotTaken"
    message = "The selected time is no longer available. Please choose another time."


class InvalidState(Conflict):
    code = "InvalidState"


class ValidationFailed(AppError):
    status_code = 422
    code = "ValidationFailed"
    message = "The request contains invalid data."


class TooManyRequests(AppError):
    status_code = 429
    code = "TooManyRequests"
    message = "Too many requests. Please try again later."


class ErpUnavailable(AppError):
    status_code = 503
    code = "ErpUnavailable"
    message = "The hospital system is temporarily unavailable. Please try again later."


class PaymentGatewayUnavailable(AppError):
    status_code = 503
    code = "PaymentGatewayUnavailable"
    message = "The payment provider is temporarily unavailable. Please try again later."
