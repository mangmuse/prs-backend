import pytest


@pytest.fixture(autouse=True)
def setup_database():
    """CSV 파서 테스트는 DB가 필요 없으므로 상위 fixture를 오버라이드한다."""
    yield
