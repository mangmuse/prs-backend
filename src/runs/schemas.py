from datetime import datetime
from typing import Any

from src.common.schemas import CamelCaseModel
from src.common.types import JsonValue, LogicConstraint
from src.runs.models import ResultStatus


class ProfileSnapshot(CamelCaseModel):
    """Run 실행 당시 Profile 스냅샷."""

    semantic_threshold: float
    global_constraints: list[LogicConstraint]


class FormatCheckResult(CamelCaseModel):
    passed: bool
    parsed_output: dict[str, Any] | list[Any] | str | None = None
    error_message: str | None = None


class SemanticCheckResult(CamelCaseModel):
    passed: bool
    semantic_score: float
    error_message: str | None = None


class ConstraintResult(CamelCaseModel):
    constraint_type: str
    target: str
    passed: bool
    message: str | None = None


class ConstraintLayerResult(CamelCaseModel):
    passed: bool
    results: list[ConstraintResult] = []
    error_message: str | None = None


class WaterfallResult(CamelCaseModel):
    """Waterfall 평가 최종 결과"""

    status: ResultStatus
    format_result: FormatCheckResult
    semantic_result: SemanticCheckResult | None = None
    constraint_result: ConstraintLayerResult | None = None


class CreateRunRequest(CamelCaseModel):
    """Run 생성 요청"""

    prompt_version_id: int
    dataset_id: int
    profile_id: int
    api_key: str | None = None


class UpdateProfileSnapshotRequest(CamelCaseModel):
    """Run의 profile_snapshot 업데이트 요청."""

    semantic_threshold: float
    global_constraints: list[LogicConstraint]


class RunCreateResponse(CamelCaseModel):
    """Run 생성 즉시 응답 (BackgroundTask 시작 후)"""

    id: int
    status: str
    created_at: datetime


class RunSummaryResponse(CamelCaseModel):
    """Run 목록 조회용 응답"""

    id: int
    prompt_id: int
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
    format_pass_rate: float | None
    semantic_pass_rate: float | None
    constraint_pass_rate: float | None
    total_rows: int
    created_at: datetime


class ProfileInRun(CamelCaseModel):
    """Run 상세 응답에 포함되는 프로필 정보"""

    id: int
    name: str
    semantic_threshold: float
    global_constraints: list[LogicConstraint]


class RunMetrics(CamelCaseModel):
    """Run 메트릭스"""

    pass_rate: float
    avg_semantic: float
    format_pass_rate: float
    semantic_pass_rate: float
    constraint_pass_rate: float


class AssembledPrompt(CamelCaseModel):
    """조립된 프롬프트"""

    system_instruction: str
    user_message: str


class RunResultResponse(CamelCaseModel):
    """개별 RunResult 응답"""

    id: int
    row_index: int
    dataset_row_id: int
    input_snapshot: dict[str, JsonValue]
    expected_snapshot: dict[str, JsonValue] | str | None
    assembled_prompt: AssembledPrompt
    status: ResultStatus
    is_format_passed: bool
    semantic_score: float
    constraint_results: dict[str, JsonValue]
    raw_output: str
    parsed_output: dict[str, JsonValue] | None


class RunDetailResponse(CamelCaseModel):
    """Run 상세 조회 응답 (GET /runs/{run_id})"""

    id: int
    prompt_id: int
    prompt_version_id: int
    dataset_id: int
    profile_id: int
    prompt_name: str
    version_number: int
    dataset_name: str
    status: str
    created_at: datetime
    profile: ProfileInRun
    metrics: RunMetrics
    results: list[RunResultResponse]


class RelatedRunResponse(CamelCaseModel):
    """같은 조합의 다른 버전 Run"""

    id: int
    version_number: int
    status: str
    pass_rate: float | None
    created_at: datetime


class UnexecutedVersionResponse(CamelCaseModel):
    """아직 실행 안 된 버전"""

    id: int
    version_number: int


class RelatedVersionsResponse(CamelCaseModel):
    """GET /runs/{id}/related-versions 응답"""

    executed_runs: list[RelatedRunResponse]
    unexecuted_versions: list[UnexecutedVersionResponse]


class RowComparisonData(CamelCaseModel):
    """개별 row의 비교 데이터 (raw) - category는 FE에서 계산"""

    row_index: int
    dataset_row_id: int
    base_status: ResultStatus
    target_status: ResultStatus
    base_semantic_score: float
    target_semantic_score: float


class RegressionComparisonResponse(CamelCaseModel):
    """회귀 분석 API 응답 - raw 데이터 + p_value만 제공"""

    p_value: float
    row_comparisons: list[RowComparisonData]


class ReEvaluateRequest(CamelCaseModel):
    """재평가 요청 (프로필 값 변경 시 미리보기)"""

    semantic_threshold: float
    global_constraints: list[LogicConstraint]


class ReEvaluatedRow(CamelCaseModel):
    """재평가된 개별 row 결과"""

    id: int
    status: ResultStatus
    constraint_results: dict[str, JsonValue] | None


class ReEvaluateResponse(CamelCaseModel):
    """재평가 응답"""

    results: list[ReEvaluatedRow]
    pass_rate: float
