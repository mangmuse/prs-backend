import json

from src.prompts.models import OutputSchemaType
from src.runs.schemas import FormatCheckResult


def check_format(
    raw_output: str,
    output_schema: OutputSchemaType,
    expected_output: str | None = None,
) -> FormatCheckResult:
    """Format Layer: 출력 형식 검증"""

    if output_schema == OutputSchemaType.JSON_OBJECT:
        return _check_json_object(raw_output)

    if output_schema == OutputSchemaType.JSON_ARRAY:
        return _check_json_array(raw_output)

    if output_schema == OutputSchemaType.LABEL:
        return _check_label(raw_output, expected_output)

    return FormatCheckResult(passed=True, parsed_output=raw_output)


def _check_json_object(raw_output: str) -> FormatCheckResult:
    try:
        parsed = json.loads(raw_output.strip())
        if isinstance(parsed, dict):
            return FormatCheckResult(passed=True, parsed_output=parsed)
        return FormatCheckResult(
            passed=False,
            error_message=f"JSON Object가 아닌 {type(parsed).__name__} 타입입니다"
        )
    except json.JSONDecodeError as e:
        return FormatCheckResult(passed=False, error_message=f"JSON 파싱 실패: {e}")


def _check_json_array(raw_output: str) -> FormatCheckResult:
    try:
        parsed = json.loads(raw_output.strip())
        if isinstance(parsed, list):
            return FormatCheckResult(passed=True, parsed_output=parsed)
        return FormatCheckResult(
            passed=False,
            error_message=f"JSON Array가 아닌 {type(parsed).__name__} 타입입니다"
        )
    except json.JSONDecodeError as e:
        return FormatCheckResult(passed=False, error_message=f"JSON 파싱 실패: {e}")


def _check_label(raw_output: str, expected_output: str | None) -> FormatCheckResult:
    cleaned = raw_output.strip()
    if cleaned == expected_output:
        return FormatCheckResult(passed=True, parsed_output=cleaned)
    return FormatCheckResult(
        passed=False,
        error_message=f"Label 불일치: '{cleaned}' != '{expected_output}'"
    )
