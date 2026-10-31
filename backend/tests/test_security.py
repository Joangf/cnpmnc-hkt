import time

import pytest

from app.core.errors import Unauthorized
from app.core.logging import REDACTED, redact_pii
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_booking_reference,
    sign_payload,
    verify_signature,
)

SECRET = "test-secret"
BODY = b'{"event_id":"e1"}'


def test_valid_signature_is_accepted() -> None:
    ts = str(int(time.time()))
    assert verify_signature(SECRET, ts, BODY, sign_payload(SECRET, ts, BODY), tolerance=300)


@pytest.mark.parametrize(
    "ts_offset,body,secret",
    [(0, b'{"event_id":"e2"}', SECRET), (0, BODY, "wrong"), (-1000, BODY, SECRET)],
)
def test_tampered_or_stale_signature_is_rejected(ts_offset: int, body: bytes, secret: str) -> None:
    ts = str(int(time.time()) + ts_offset)
    signature = sign_payload(secret, ts, BODY)
    assert not verify_signature(SECRET, ts, body, signature, tolerance=300)


def test_missing_signature_is_rejected() -> None:
    assert not verify_signature(SECRET, None, BODY, None, tolerance=300)


def test_token_type_is_enforced() -> None:
    assert decode_token(create_access_token(1, "PATIENT"), "access")["sub"] == "1"
    with pytest.raises(Unauthorized):
        decode_token(create_refresh_token(1), "access")


def test_booking_reference_format() -> None:
    ref = generate_booking_reference()
    assert ref.startswith("HK") and len(ref) == 10


def test_pii_is_redacted_from_logs() -> None:
    event = {
        "event": "x",
        "email": "a@b.c",
        "nested": {"phone_number": "123", "ok": 1},
        "items": [{"token": "t"}],
    }
    out = redact_pii(None, "info", event)
    assert out["email"] == REDACTED
    assert out["nested"] == {"phone_number": REDACTED, "ok": 1}
    assert out["items"] == [{"token": REDACTED}]
