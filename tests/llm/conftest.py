import pytest


@pytest.fixture(autouse=True)
async def setup_database():
    """LLM 테스트는 DB 불필요 - 상위 conftest의 DB fixture 오버라이드."""
    yield
