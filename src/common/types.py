"""PRS 백엔드 공통 타입 정의."""

from typing import TypedDict


class HealthResponse(TypedDict):
    """헬스 체크 엔드포인트 응답."""

    status: str
    timestamp: str


class LogicConstraint(TypedDict, total=False):
    """데이터셋 행 및 평가 프로필용 로직 제약조건 정의.

    타입:
    - contains: 대상 필드에 값이 포함되어야 함
    - not_contains: 대상 필드에 값이 포함되지 않아야 함
    - range: 대상 필드의 숫자 값이 min/max 범위 내여야 함
    - regex: 대상 필드가 패턴과 일치해야 함
    - max_length: 대상 필드가 값 길이를 초과하지 않아야 함
    """

    type: str
    target: str
    value: str | int | float
    min: float | None
    max: float | None
    pattern: str | None


class LogicCheckResult(TypedDict):
    """단일 로직 제약조건 검사 결과."""

    constraint_type: str
    passed: bool
    message: str | None


class ParsedOutput(TypedDict, total=False):
    """파싱된 LLM 출력 구조.

    실제 구조는 output_schema 타입에 따라 다르지만,
    공통 필드는 여기에 정의됨.
    """

    verdict: str | None
    confidence: float | None
    reasoning: str | None
