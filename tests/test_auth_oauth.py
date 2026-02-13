from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models import User
from src.auth.service import find_or_create_user
from src.main import app
from src.redis import get_redis

MOCK_USERINFO = {
    "sub": "google-uid-12345",
    "email": "test@example.com",
    "email_verified": True,
    "name": "Test User",
    "picture": "https://example.com/photo.jpg",
}


def _make_mock_user(**overrides) -> MagicMock:
    defaults = {
        "id": 1,
        "email": "test@example.com",
        "provider": "google",
        "provider_id": "google-uid-12345",
        "name": "Test User",
        "picture_url": "https://example.com/photo.jpg",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


class TestFindOrCreateUser:
    """find_or_create_user 서비스 함수 테스트 (DB 통합 테스트 - Docker Postgres 필요)."""

    @pytest.mark.asyncio
    async def test_creates_new_user(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """신규 사용자 생성."""
        async with test_session_factory() as session:
            user = await find_or_create_user(
                session=session,
                email="new@example.com",
                provider_id="google-new-123",
                name="New User",
                picture_url="https://example.com/new.jpg",
            )

        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.provider_id == "google-new-123"
        assert user.name == "New User"
        assert user.picture_url == "https://example.com/new.jpg"
        assert user.provider == "google"

    @pytest.mark.asyncio
    async def test_returns_existing_user_by_provider_id(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """provider_id가 동일하면 기존 사용자 반환."""
        async with test_session_factory() as session:
            existing = User(
                email="existing@example.com",
                provider="google",
                provider_id="google-existing-456",
                name="Existing User",
            )
            session.add(existing)
            await session.commit()
            await session.refresh(existing)

        async with test_session_factory() as session:
            user = await find_or_create_user(
                session=session,
                email="existing@example.com",
                provider_id="google-existing-456",
                name="Updated Name",
            )

        assert user.id == existing.id
        assert user.email == "existing@example.com"

    @pytest.mark.asyncio
    async def test_email_fallback_updates_provider_id(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """provider_id는 다르지만 email이 같으면 기존 사용자의 provider_id 업데이트."""
        async with test_session_factory() as session:
            existing = User(
                email="fallback@example.com",
                provider="google",
                provider_id="old-provider-id",
                name="Old Name",
            )
            session.add(existing)
            await session.commit()
            await session.refresh(existing)

        async with test_session_factory() as session:
            user = await find_or_create_user(
                session=session,
                email="fallback@example.com",
                provider_id="new-provider-id",
                name="Updated Name",
                picture_url="https://example.com/updated.jpg",
            )

        assert user.id == existing.id
        assert user.provider_id == "new-provider-id"
        assert user.name == "Updated Name"
        assert user.picture_url == "https://example.com/updated.jpg"

    @pytest.mark.asyncio
    async def test_creates_user_without_optional_fields(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """name, picture_url 없이도 사용자 생성 가능."""
        async with test_session_factory() as session:
            user = await find_or_create_user(
                session=session,
                email="minimal@example.com",
                provider_id="google-minimal-789",
            )

        assert user.id is not None
        assert user.email == "minimal@example.com"
        assert user.name is None
        assert user.picture_url is None


class TestGoogleLogin:
    """GET /auth/google 엔드포인트 테스트."""

    @pytest.fixture(autouse=True)
    async def setup_database(self) -> AsyncGenerator[None, None]:
        """DB 불필요."""
        yield

    @pytest.fixture
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_redirects_to_google(self, client: AsyncClient) -> None:
        """GET /auth/google → 302 구글 인증 페이지로 리다이렉트."""
        with patch("src.auth.oauth.oauth.google.authorize_redirect") as mock_redirect:
            from starlette.responses import RedirectResponse

            mock_redirect.return_value = RedirectResponse(
                url="https://accounts.google.com/o/oauth2/auth?client_id=test",
                status_code=302,
            )
            response = await client.get("/auth/google")

        assert response.status_code == 302
        assert "accounts.google.com" in response.headers["location"]


class TestGoogleCallback:
    """GET /auth/google/callback 엔드포인트 테스트 (DB 모킹)."""

    @pytest.fixture(autouse=True)
    async def setup_database(self) -> AsyncGenerator[None, None]:
        """DB 불필요."""
        yield

    @pytest.fixture
    async def fake_redis(self):
        return fakeredis.aioredis.FakeRedis(decode_responses=True)

    @pytest.fixture
    async def client(self, fake_redis) -> AsyncGenerator[AsyncClient, None]:
        async def get_test_redis() -> AsyncGenerator[
            fakeredis.aioredis.FakeRedis, None
        ]:
            yield fake_redis

        app.dependency_overrides[get_redis] = get_test_redis
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            yield ac
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_successful_callback_redirects_with_tokens(
        self, client: AsyncClient
    ) -> None:
        """구글 콜백 성공 → 토큰 발급, 프론트엔드 리다이렉트."""
        mock_token = {"userinfo": MOCK_USERINFO}
        mock_user = _make_mock_user()

        with (
            patch(
                "src.auth.router.oauth.google.authorize_access_token",
                new_callable=AsyncMock,
                return_value=mock_token,
            ),
            patch(
                "src.auth.router.service.find_or_create_user",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith("http://localhost:5173/auth/callback?code=")
        assert "refresh_token" in response.cookies

        set_cookie = response.headers["set-cookie"]
        assert "path=/auth" in set_cookie.lower()
        assert "httponly" in set_cookie.lower()
        assert "samesite=strict" in set_cookie.lower()

    @pytest.mark.asyncio
    async def test_callback_with_existing_user(self, client: AsyncClient) -> None:
        """기존 사용자로 콜백 → 토큰 발급."""
        mock_token = {"userinfo": MOCK_USERINFO}
        existing_user = _make_mock_user(id=42)

        with (
            patch(
                "src.auth.router.oauth.google.authorize_access_token",
                new_callable=AsyncMock,
                return_value=mock_token,
            ),
            patch(
                "src.auth.router.service.find_or_create_user",
                new_callable=AsyncMock,
                return_value=existing_user,
            ) as mock_find,
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 302
        mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_with_unverified_email(self, client: AsyncClient) -> None:
        """email_verified=False → 400."""
        unverified_info = {**MOCK_USERINFO, "email_verified": False}
        mock_token = {"userinfo": unverified_info}

        with patch(
            "src.auth.router.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=mock_token,
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 400
        assert response.json()["detail"] == "인증되지 않은 이메일입니다"

    @pytest.mark.asyncio
    async def test_callback_with_missing_userinfo(self, client: AsyncClient) -> None:
        """userinfo 없음 → 400."""
        mock_token = {}

        with patch(
            "src.auth.router.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=mock_token,
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 400
        assert response.json()["detail"] == "구글 사용자 정보를 가져올 수 없습니다"

    @pytest.mark.asyncio
    async def test_callback_with_oauth_error(self, client: AsyncClient) -> None:
        """OAuth 토큰 교환 실패 → 400."""
        with patch(
            "src.auth.router.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            side_effect=Exception("OAuth error"),
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 400
        assert response.json()["detail"] == "구글 인증에 실패했습니다"

    @pytest.mark.asyncio
    async def test_callback_with_missing_email(self, client: AsyncClient) -> None:
        """email 없음 → 400."""
        no_email_info = {**MOCK_USERINFO, "email": None}
        mock_token = {"userinfo": no_email_info}

        with patch(
            "src.auth.router.oauth.google.authorize_access_token",
            new_callable=AsyncMock,
            return_value=mock_token,
        ):
            response = await client.get("/auth/google/callback")

        assert response.status_code == 400
        assert response.json()["detail"] == "구글 사용자 정보가 불완전합니다"
