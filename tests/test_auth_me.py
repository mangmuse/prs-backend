"""GET /auth/me 및 get_current_identity 우선순위 테스트."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.models import User
from src.auth.service import create_access_token


@pytest.fixture
async def user_factory(
    test_session_factory: async_sessionmaker[AsyncSession],
):
    """User 생성 팩토리."""

    async def _create(
        email: str = "test@example.com",
        name: str = "Test User",
    ) -> User:
        async with test_session_factory() as session:
            user = User(
                email=email,
                provider="google",
                provider_id=f"google_{email}",
                name=name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return _create


@pytest.mark.asyncio
async def test_get_me_with_valid_token(
    client: AsyncClient,
    user_factory,
) -> None:
    """GET /auth/me — 유효한 Bearer 토큰으로 성공 응답."""
    user = await user_factory()
    assert user.id is not None
    token, _ = create_access_token(user.id, "user")

    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_me_without_auth_returns_401(
    client: AsyncClient,
) -> None:
    """GET /auth/me — 인증 없이 접근 시 401."""
    response = await client.get("/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_identity_bearer_token_returns_user(
    client: AsyncClient,
    user_factory,
) -> None:
    """Bearer 토큰 → User 반환 (인증된 엔드포인트 접근 성공)."""
    user = await user_factory()
    assert user.id is not None
    token, _ = create_access_token(user.id, "user")

    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_identity_cookie_returns_guest(
    client: AsyncClient,
    guest_cookies: dict[str, str],
) -> None:
    """쿠키 → Guest 반환 (게스트 전용 엔드포인트 접근 성공)."""
    response = await client.get("/datasets")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_current_identity_bearer_priority_over_cookie(
    client: AsyncClient,
    guest_cookies: dict[str, str],
    user_factory,
) -> None:
    """Bearer 토큰과 쿠키 둘 다 있으면 Bearer 우선 → User 반환."""
    user = await user_factory()
    assert user.id is not None
    token, _ = create_access_token(user.id, "user")

    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
