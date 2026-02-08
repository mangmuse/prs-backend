"""PRS 백엔드 공통 타입 정의."""

from enum import StrEnum
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


class ConstraintType(StrEnum):
    """Constraint Layer constraint 타입."""

    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    RANGE = "range"
    REGEX = "regex"
    MAX_LENGTH = "max_length"


class ContainsConstraint(BaseModel):
    """contains: target 필드에 value가 포함되어야 함."""

    type: Literal["contains"]
    target: str
    value: str


class NotContainsConstraint(BaseModel):
    """not_contains: target 필드에 value가 포함되지 않아야 함."""

    type: Literal["not_contains"]
    target: str
    value: str


class RangeConstraint(BaseModel):
    """range: target 필드의 숫자 값이 min/max 범위 내여야 함."""

    type: Literal["range"]
    target: str
    min: float | None = None
    max: float | None = None


class RegexConstraint(BaseModel):
    """regex: target 필드가 pattern과 일치해야 함."""

    type: Literal["regex"]
    target: str
    pattern: str


class MaxLengthConstraint(BaseModel):
    """max_length: target 필드의 길이가 max 이하여야 함."""

    type: Literal["max_length"]
    target: str
    max: int


LogicConstraint = Annotated[
    ContainsConstraint
    | NotContainsConstraint
    | RangeConstraint
    | RegexConstraint
    | MaxLengthConstraint,
    Field(discriminator="type"),
]


class HealthResponse(TypedDict):
    """헬스 체크 엔드포인트 응답."""

    status: str
    timestamp: str


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
