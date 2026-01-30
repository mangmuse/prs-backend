from typing import Any

from pydantic import BaseModel

from src.runs.models import ResultStatus


class FormatCheckResult(BaseModel):
    passed: bool
    parsed_output: dict[str, Any] | list[Any] | str | None = None
    error_message: str | None = None


class SemanticCheckResult(BaseModel):
    passed: bool
    semantic_score: float
    error_message: str | None = None


class ConstraintResult(BaseModel):
    constraint_type: str
    target: str
    passed: bool
    message: str | None = None


class LogicLayerResult(BaseModel):
    passed: bool
    results: list[ConstraintResult] = []
    error_message: str | None = None


class WaterfallResult(BaseModel):
    """Waterfall 평가 최종 결과"""

    status: ResultStatus
    format_result: FormatCheckResult
    semantic_result: SemanticCheckResult | None = None
    logic_result: LogicLayerResult | None = None
