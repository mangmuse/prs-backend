import logging

from src.common.types import LogicConstraint
from src.prompts.models import OutputSchemaType
from src.runs.evaluator.format_layer import check_format
from src.runs.evaluator.logic_layer import FieldValue, check_logic
from src.runs.evaluator.semantic_layer import check_semantic
from src.runs.models import ResultStatus
from src.runs.schemas import (
    FormatCheckResult,
    WaterfallResult,
)

logger = logging.getLogger(__name__)


def evaluate_waterfall(
    raw_output: str,
    output_schema: OutputSchemaType,
    expected_output: str,
    threshold: float,
    constraints: list[LogicConstraint],
) -> WaterfallResult:
    """3-Layer Waterfall 평가 (fail-fast)"""
    logger.info(
        "Waterfall 평가 시작 | schema=%s, threshold=%.2f, constraints=%d개",
        output_schema.value,
        threshold,
        len(constraints),
    )
    logger.debug("raw_output=%s, expected=%s", raw_output[:100], expected_output[:100])

    # Layer 1: Format Check
    format_result = check_format(raw_output, output_schema, expected_output)
    logger.info(
        "Layer1 Format | passed=%s, error=%s",
        format_result.passed,
        format_result.error_message or "없음",
    )

    if not format_result.passed:
        logger.info("Waterfall 종료 | status=FORMAT (Layer1에서 실패)")
        return WaterfallResult(
            status=ResultStatus.FORMAT,
            format_result=format_result,
        )

    # Layer 2: Semantic Check
    semantic_result = check_semantic(
        raw_output, expected_output, output_schema, threshold
    )
    logger.info(
        "Layer2 Semantic | passed=%s, score=%.4f, threshold=%.2f",
        semantic_result.passed,
        semantic_result.semantic_score,
        threshold,
    )

    if not semantic_result.passed:
        logger.info("Waterfall 종료 | status=SEMANTIC (Layer2에서 실패)")
        return WaterfallResult(
            status=ResultStatus.SEMANTIC,
            format_result=format_result,
            semantic_result=semantic_result,
        )

    # Layer 3: Logic Check
    parsed_output = _get_parsed_output(format_result)
    logic_result = check_logic(parsed_output, constraints)
    logger.info(
        "Layer3 Logic | passed=%s, results=%s",
        logic_result.passed,
        [r.model_dump() for r in (logic_result.results or [])],
    )

    if not logic_result.passed:
        logger.info("Waterfall 종료 | status=LOGIC (Layer3에서 실패)")
        return WaterfallResult(
            status=ResultStatus.LOGIC,
            format_result=format_result,
            semantic_result=semantic_result,
            logic_result=logic_result,
        )

    # All passed
    logger.info("Waterfall 종료 | status=PASS (모든 레이어 통과)")
    return WaterfallResult(
        status=ResultStatus.PASS,
        format_result=format_result,
        semantic_result=semantic_result,
        logic_result=logic_result,
    )


def _get_parsed_output(format_result: FormatCheckResult) -> dict[str, FieldValue]:
    """FormatCheckResult에서 parsed_output 추출"""
    if isinstance(format_result.parsed_output, dict):
        return format_result.parsed_output
    return {}
