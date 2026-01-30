from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.common.types import JsonValue, LogicConstraint
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


class CreateRunRequest(BaseModel):
    """Run 생성 요청"""

    prompt_version_id: int
    dataset_id: int
    profile_id: int


class RunCreateResponse(BaseModel):
    """Run 생성 즉시 응답 (BackgroundTask 시작 후)"""

    id: int
    status: str
    created_at: datetime


class RunSummaryResponse(BaseModel):
    """Run 목록 조회용 응답"""

    id: int
    prompt_version_id: int
    prompt_name: str
    version_number: int
    dataset_id: int
    dataset_name: str
    profile_id: int
    profile_name: str
    status: str
    pass_rate: float | None
    avg_semantic: float | None
    total_rows: int
    created_at: datetime


class ProfileInRun(BaseModel):
    """Run 상세 응답에 포함되는 프로필 정보"""

    id: int
    name: str
    semantic_threshold: float
    global_constraints: list[LogicConstraint]


class RunMetrics(BaseModel):
    """Run 메트릭스"""

    pass_rate: float
    avg_semantic: float


class AssembledPrompt(BaseModel):
    """조립된 프롬프트"""

    system_instruction: str
    user_message: str


class RunResultResponse(BaseModel):
    """개별 RunResult 응답"""

    id: int
    dataset_row_id: int
    input_snapshot: dict[str, JsonValue]
    expected_snapshot: dict[str, JsonValue] | str | None
    assembled_prompt: AssembledPrompt
    status: ResultStatus
    is_format_passed: bool
    semantic_score: float
    logic_results: dict[str, JsonValue]
    raw_output: str
    parsed_output: dict[str, JsonValue] | None


class RunDetailResponse(BaseModel):
    """Run 상세 조회 응답 (GET /runs/{run_id})"""

    id: int
    profile: ProfileInRun
    metrics: RunMetrics
    results: list[RunResultResponse]
