from pydantic import BaseModel


class FormatCheckResult(BaseModel):
    passed: bool
    parsed_output: dict | list | str | None = None
    error_message: str | None = None


class SemanticCheckResult(BaseModel):
    passed: bool
    semantic_score: float
    error_message: str | None = None
