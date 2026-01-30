from typing import Any

from pydantic import BaseModel


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
