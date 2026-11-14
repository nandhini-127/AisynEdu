from datetime import timedelta
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    raw = "MySuperSecretPassword123!"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_token_creation_and_decoding():
    subject = "user-12345"
    token = create_access_token(subject=subject, expires_delta=timedelta(minutes=15))
    payload = decode_token(token)
    assert payload.get("sub") == subject
    assert payload.get("type") == "access"
    assert "exp" in payload


def test_refresh_token_type():
    subject = "user-999"
    token = create_refresh_token(subject=subject)
    payload = decode_token(token)
    assert payload.get("sub") == subject
    assert payload.get("type") == "refresh"

