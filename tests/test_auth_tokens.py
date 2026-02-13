from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest

from src.auth.service import create_access_token, create_refresh_token, decode_token


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """DB 불필요 - 상위 conftest의 autouse fixture 오버라이드"""
    yield


class TestCreateAccessToken:
    def test_creates_valid_token(self):
        """access token 생성 후 디코드하면 올바른 sub, type 반환"""
        token, expire = create_access_token(1, "user")
        assert isinstance(token, str)
        assert len(token) > 0
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == "1"
        assert payload.type == "user"

    def test_default_expiry_15_minutes(self):
        """access token 기본 만료는 15분"""
        token, expire = create_access_token(1, "user")
        payload = decode_token(token)
        assert payload is not None
        diff = payload.exp - payload.iat
        assert timedelta(minutes=14) < diff < timedelta(minutes=16)


class TestCreateRefreshToken:
    def test_creates_valid_refresh_token(self):
        """refresh token 생성 후 디코드하면 _refresh 접미사가 붙은 type 반환"""
        token, expire = create_refresh_token(1, "user")
        payload = decode_token(token)
        assert payload is not None
        assert payload.sub == "1"
        assert payload.type == "user_refresh"

    def test_default_expiry_7_days(self):
        """refresh token 기본 만료는 7일"""
        token, expire = create_refresh_token(1, "user")
        payload = decode_token(token)
        assert payload is not None
        diff = payload.exp - payload.iat
        assert timedelta(days=6) < diff < timedelta(days=8)


class TestDecodeToken:
    def test_invalid_token_returns_none(self):
        """유효하지 않은 토큰은 None 반환"""
        assert decode_token("invalid.token.here") is None

    def test_empty_string_returns_none(self):
        """빈 문자열은 None 반환"""
        assert decode_token("") is None

    def test_expired_token_returns_none(self):
        """만료된 토큰은 None 반환"""
        token, _ = create_access_token(1, "user", expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None
