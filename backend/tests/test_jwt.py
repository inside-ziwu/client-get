import pytest
from jose import jwt as jose_jwt

from app.core.config import get_settings
from app.core.errors import AppError
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


class TestAccessTokenIid:
    def test_access_token_contains_iid(self):
        token = create_access_token({"sub": "u1", "kind": "platform"})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["iid"] == settings.instance_id

    def test_access_token_iid_matches_instance(self):
        token = create_access_token({"sub": "u1", "kind": "platform"})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["iid"] == "default"

    def test_caller_iid_is_overridden(self):
        token = create_access_token({"sub": "u1", "kind": "platform", "iid": "should-be-overridden"})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["iid"] == settings.instance_id

    def test_service_token_contains_iid(self):
        token = create_access_token({"sub": "svc", "kind": "service", "service_name": "sending-worker", "scopes": ["sending:claim"]})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["iid"] == settings.instance_id
        assert payload["kind"] == "service"


class TestRefreshTokenIid:
    def test_refresh_token_contains_iid(self):
        token = create_refresh_token({"sub": "u1", "kind": "platform"})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["iid"] == settings.instance_id
        assert payload["type"] == "refresh"


class TestCreateRefreshToken:
    def test_contains_type_refresh(self):
        token = create_refresh_token({"sub": "u1", "kind": "platform"})
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["type"] == "refresh"
        assert payload["sub"] == "u1"
        assert payload["kind"] == "platform"
        assert "exp" in payload
        assert "iat" in payload


class TestDecodeRefreshToken:
    def test_success(self):
        token = create_refresh_token({"sub": "u1", "kind": "platform"})
        payload = decode_refresh_token(token)
        assert payload["sub"] == "u1"
        assert payload["kind"] == "platform"
        assert payload["type"] == "refresh"

    def test_rejects_access_token(self):
        token = create_access_token({"sub": "u1", "kind": "platform"})
        with pytest.raises(AppError) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.status_code == 401

    def test_rejects_expired_token(self):
        settings = get_settings()
        payload = {
            "sub": "u1",
            "kind": "platform",
            "type": "refresh",
            "iat": 1000000000,
            "exp": 1000000001,
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(AppError) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.status_code == 401
