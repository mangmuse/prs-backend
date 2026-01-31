import os
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from src.auth.models import Guest
from src.database import get_session
from src.datasets.models import Dataset, DatasetRow
from src.main import app
from src.common.types import LogicConstraint
from src.profiles.models import EvaluatorProfile
from src.prompts.models import OutputSchemaType, Prompt, PromptVersion
from src.llm.base import LLMClient

# 테스트 DB URL (환경변수 또는 기본값: docker-compose의 PostgreSQL)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/prs_test",
)


@pytest.fixture(scope="session")
def test_engine():
    """세션 범위 async engine - NullPool로 연결 풀링 비활성화."""
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """세션 범위 session factory."""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database(test_engine) -> AsyncGenerator[None, None]:
    """각 테스트 전 DB 테이블 생성, 후 삭제 (enum 포함)."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS outputschematype CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS runstatus CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS resultstatus CASCADE"))
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
async def client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    """테스트용 HTTP 클라이언트."""

    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def guest_cookies(client: AsyncClient) -> dict[str, str]:
    """게스트 세션 생성 후 쿠키 반환."""
    response = await client.post("/auth/guest")
    assert response.status_code == 200
    return {"guest_id": response.json()["guest_id"]}


@pytest.fixture
def guest_factory(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Coroutine[Any, Any, Guest]]:
    """게스트 생성 팩토리 - FK 제약조건 충족용."""

    async def _create() -> Guest:
        async with test_session_factory() as session:
            guest = Guest()
            session.add(guest)
            await session.commit()
            await session.refresh(guest)
            return guest

    return _create


@pytest.fixture
def prompt_factory(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Coroutine[Any, Any, tuple[Prompt, PromptVersion]]]:
    """프롬프트 + 버전 생성 팩토리."""

    async def _create(
        guest_id: str | UUID,
        name: str = "Test Prompt",
        system_instruction: str = "You are a helpful assistant.",
        user_template: str = "{{input}}",
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        output_schema: OutputSchemaType = OutputSchemaType.FREEFORM,
    ) -> tuple[Prompt, PromptVersion]:
        guest_uuid = UUID(guest_id) if isinstance(guest_id, str) else guest_id
        async with test_session_factory() as session:
            prompt = Prompt(guest_id=guest_uuid, name=name)
            session.add(prompt)
            await session.commit()
            await session.refresh(prompt)

            assert prompt.id is not None
            version = PromptVersion(
                prompt_id=prompt.id,
                version_number=1,
                system_instruction=system_instruction,
                user_template=user_template,
                model=model,
                temperature=temperature,
                output_schema=output_schema,
            )
            session.add(version)
            await session.commit()
            await session.refresh(version)

            return prompt, version

    return _create


@pytest.fixture
def dataset_factory(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Coroutine[Any, Any, Dataset]]:
    """데이터셋 생성 팩토리."""

    async def _create(
        guest_id: str | UUID,
        name: str = "Test Dataset",
        rows: list[dict[str, Any]] | None = None,
    ) -> Dataset:
        guest_uuid = UUID(guest_id) if isinstance(guest_id, str) else guest_id
        async with test_session_factory() as session:
            dataset = Dataset(guest_id=guest_uuid, name=name)
            session.add(dataset)
            await session.commit()
            await session.refresh(dataset)

            assert dataset.id is not None
            if rows:
                for i, row_data in enumerate(rows):
                    row = DatasetRow(
                        dataset_id=dataset.id,
                        row_index=i,
                        input_data=row_data.get("input", {}),
                        expected_output=row_data.get("expected", ""),
                    )
                    session.add(row)
                await session.commit()

            return dataset

    return _create


@pytest.fixture
def profile_factory(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., Coroutine[Any, Any, EvaluatorProfile]]:
    """프로필 생성 팩토리."""

    async def _create(
        guest_id: str | UUID,
        name: str = "Test Profile",
        semantic_threshold: float = 0.8,
        global_constraints: list[LogicConstraint] | None = None,
    ) -> EvaluatorProfile:
        guest_uuid = UUID(guest_id) if isinstance(guest_id, str) else guest_id
        async with test_session_factory() as session:
            profile = EvaluatorProfile(
                guest_id=guest_uuid,
                name=name,
                semantic_threshold=semantic_threshold,
                global_constraints=global_constraints,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
            return profile

    return _create


class MockLLMClient:
    """테스트용 Mock LLM 클라이언트."""

    def __init__(self, response: str | list[str]):
        self.responses = [response] if isinstance(response, str) else response
        self.call_count = 0

    async def generate(
        self,
        system_instruction: str,
        user_message: str,
        temperature: float = 1.0,
    ) -> str:
        if self.call_count < len(self.responses):
            result = self.responses[self.call_count]
            self.call_count += 1
            return result
        return self.responses[-1]


@pytest.fixture
def mock_llm_response() -> str:
    """모킹할 LLM 응답 - 테스트에서 오버라이드 가능."""
    return '{"verdict": "TRUE", "confidence": 0.95}'


@pytest.fixture
def mock_llm_client(mock_llm_response: str) -> MockLLMClient:
    """MockLLMClient 인스턴스."""
    return MockLLMClient(mock_llm_response)
