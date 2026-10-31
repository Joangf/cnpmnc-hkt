"""Request context middleware: request id, contextual logging, one access-log line per request.

Implemented as pure ASGI (not BaseHTTPMiddleware) so contextvars bound here are visible
to the endpoint, and values the endpoint writes to `request.state` are visible here.
"""

import re
import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger("http")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
_QUIET_ROUTES = {"/metrics", "/healthz", "/readyz"}


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex

        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("latin-1")),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("unhandled_exception")
            raise
        finally:
            route = scope.get("route")
            path = getattr(route, "path", None) or "unmatched"
            if path not in _QUIET_ROUTES:
                log = logger.error if status_code >= 500 else logger.info
                log(
                    "request",
                    method=scope["method"],
                    route=path,
                    status=status_code,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    user_id=state.get("user_id"),
                )
