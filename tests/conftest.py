import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from src.database import get_session
from src.main import app

# 테스트 DB URL (환경변수 또는 기본값: docker-compose의 PostgreSQL)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/prs_test",
)


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프 - 모든 테스트가 같은 루프 사용."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    """각 테스트 전 DB 테이블 생성, 후 삭제."""
    async with test_engine.begin() as conn:
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
