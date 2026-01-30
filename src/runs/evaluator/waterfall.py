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


def evaluate_waterfall(
    raw_output: str,
    output_schema: OutputSchemaType,
    expected_output: str,
    threshold: float,
    constraints: list[LogicConstraint],
) -> WaterfallResult:
    """3-Layer Waterfall 평가 (fail-fast)"""

    # Layer 1: Format Check
    format_result = check_format(raw_output, output_schema, expected_output)

    if not format_result.passed:
        return WaterfallResult(
            status=ResultStatus.FORMAT,
            format_result=format_result,
        )

    # Layer 2: Semantic Check
    semantic_result = check_semantic(
        raw_output, expected_output, output_schema, threshold
    )

    if not semantic_result.passed:
        return WaterfallResult(
            status=ResultStatus.SEMANTIC,
            format_result=format_result,
            semantic_result=semantic_result,
        )

    # Layer 3: Logic Check
    parsed_output = _get_parsed_output(format_result)
    logic_result = check_logic(parsed_output, constraints)

    if not logic_result.passed:
        return WaterfallResult(
            status=ResultStatus.LOGIC,
            format_result=format_result,
            semantic_result=semantic_result,
            logic_result=logic_result,
        )

    # All passed
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
