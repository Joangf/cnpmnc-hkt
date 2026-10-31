import hashlib
import hmac
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.errors import Unauthorized

# Argon2id with library-recommended parameters (NFR-02)
password_hash = PasswordHash.recommended()

_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired token.", code="InvalidToken") from exc
    if payload.get("type") != expected_type:
        raise Unauthorized("Invalid token type.", code="InvalidToken")
    return payload


def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def verify_signature(
    secret: str, timestamp: str | None, body: bytes, signature: str | None, tolerance: int
) -> bool:
    """Validate an HMAC-SHA256 webhook signature over `"{timestamp}.{body}"` (NFR-11)."""
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > tolerance:
        return False
    return hmac.compare_digest(sign_payload(secret, timestamp, body), signature)


def generate_booking_reference() -> str:
    return "HK" + "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(8))


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
