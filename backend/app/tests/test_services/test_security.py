"""Unit tests for security module (JWT + password hashing)."""
import os
import pytest
from datetime import timedelta
from jose import JWTError

# Set test env before importing
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")

from app.core.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    create_api_key_hash, verify_api_key,
)


class TestPasswordHashing:
    def test_hash_produces_different_value(self):
        h = hash_password("mypassword")
        assert h != "mypassword"

    def test_verify_correct_password(self):
        h = hash_password("secure123")
        assert verify_password("secure123", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("secure123")
        assert verify_password("wrong123", h) is False

    def test_each_hash_is_unique(self):
        """Same password hashed twice produces different hashes (salt)."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # Different salts


class TestJWTToken:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "user-1"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"

    def test_token_has_expiration(self):
        token = create_access_token({"sub": "user-1"})
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_token_with_custom_expiry(self):
        token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(hours=2))
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_tampered_token_raises(self):
        token = create_access_token({"sub": "user-1"})
        parts = token.split(".")
        # Tamper with the payload
        tampered = f"{parts[0]}.{parts[1]}x.{parts[2]}"
        with pytest.raises(JWTError):
            decode_access_token(tampered)


class TestAPIKeyHashing:
    def test_hash_and_verify_api_key(self):
        h = create_api_key_hash("sk-test-api-key-12345")
        assert verify_api_key("sk-test-api-key-12345", h) is True
        assert verify_api_key("wrong-key", h) is False

    def test_api_key_hash_is_unique(self):
        h1 = create_api_key_hash("same_key")
        h2 = create_api_key_hash("same_key")
        assert h1 != h2
