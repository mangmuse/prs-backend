import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth import service
from src.auth.models import Guest, User
from src.datasets.models import Dataset
from src.profiles.models import EvaluatorProfile
from src.prompts.models import Prompt


@pytest.fixture
async def user(test_session_factory: async_sessionmaker[AsyncSession]) -> User:
    async with test_session_factory() as session:
        user = User(
            email="test@example.com",
            provider="google",
            provider_id="google-sub-123",
            name="Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def user_token(user: User) -> str:
    assert user.id is not None
    token, _ = service.create_access_token(user.id, "user")
    return token


@pytest.fixture
async def guest_with_data(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[Guest, dict[str, int]]:
    """게스트 + 테스트 데이터 생성 (dataset 1, prompt 1, profile 1)."""
    async with test_session_factory() as session:
        guest = Guest()
        session.add(guest)
        await session.commit()
        await session.refresh(guest)

        dataset = Dataset(guest_id=guest.id, name="Guest Dataset")
        prompt = Prompt(guest_id=guest.id, name="Guest Prompt")
        profile = EvaluatorProfile(guest_id=guest.id, name="Guest Profile")
        session.add_all([dataset, prompt, profile])
        await session.commit()

        return guest, {"datasets": 1, "prompts": 1, "profiles": 1, "runs": 0}


@pytest.mark.asyncio
async def test_migrate_success(
    client: AsyncClient,
    user_token: str,
    guest_with_data: tuple[Guest, dict[str, int]],
) -> None:
    """POST /auth/migrate - User + guest_id 쿠키 → 200 + migrated_counts."""
    guest, expected_counts = guest_with_data
    client.cookies.set("guest_id", str(guest.id))

    response = await client.post(
        "/auth/migrate",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["datasets"] == expected_counts["datasets"]
    assert data["prompts"] == expected_counts["prompts"]
    assert data["profiles"] == expected_counts["profiles"]
    assert data["runs"] == expected_counts["runs"]


@pytest.mark.asyncio
async def test_migrate_no_guest_cookie(
    client: AsyncClient,
    user_token: str,
) -> None:
    """POST /auth/migrate - guest_id 쿠키 없음 → 400."""
    response = await client.post(
        "/auth/migrate",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_migrate_nonexistent_guest(
    client: AsyncClient,
    user_token: str,
) -> None:
    """POST /auth/migrate - 존재하지 않는 guest → 404."""
    client.cookies.set("guest_id", "00000000-0000-0000-0000-000000000000")

    response = await client.post(
        "/auth/migrate",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_migrate_guest_cannot_call(
    client: AsyncClient,
    guest_cookies: dict[str, str],  # noqa: ARG001
) -> None:
    """POST /auth/migrate - 게스트(비회원)가 호출 → 401."""
    response = await client.post("/auth/migrate")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_migrate_empty_guest(
    client: AsyncClient,
    user_token: str,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """POST /auth/migrate - 데이터 0건인 게스트 → 200 + counts 전부 0."""
    async with test_session_factory() as session:
        guest = Guest()
        session.add(guest)
        await session.commit()
        await session.refresh(guest)

    client.cookies.set("guest_id", str(guest.id))

    response = await client.post(
        "/auth/migrate",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["datasets"] == 0
    assert data["prompts"] == 0
    assert data["profiles"] == 0
    assert data["runs"] == 0
