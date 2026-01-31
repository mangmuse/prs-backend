import json
import logging
import re

from src.prompts.models import OutputSchemaType
from src.runs.schemas import FormatCheckResult

logger = logging.getLogger(__name__)


def _strip_markdown_code_block(text: str) -> str:
    """Markdown 코드블록 제거 (```json ... ``` → 내용만 추출)."""
    pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(pattern, text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def check_format(
    raw_output: str,
    output_schema: OutputSchemaType,
    expected_output: str | None = None,
) -> FormatCheckResult:
    """Format Layer: 출력 형식 검증"""
    logger.debug("Format 검증 시작 | schema=%s", output_schema.value)

    if output_schema == OutputSchemaType.JSON_OBJECT:
        result = _check_json_object(raw_output)
        logger.debug("JSON Object 검증 결과 | passed=%s", result.passed)
        return result

    if output_schema == OutputSchemaType.JSON_ARRAY:
        result = _check_json_array(raw_output)
        logger.debug("JSON Array 검증 결과 | passed=%s", result.passed)
        return result

    if output_schema == OutputSchemaType.LABEL:
        result = _check_label(raw_output, expected_output)
        logger.debug(
            "Label 검증 결과 | passed=%s, raw='%s', expected='%s'",
            result.passed,
            raw_output.strip()[:50],
            expected_output[:50] if expected_output else None,
        )
        return result

    logger.debug("Freeform 스키마 | 검증 생략")
    return FormatCheckResult(passed=True, parsed_output=raw_output)


def _check_json_object(raw_output: str) -> FormatCheckResult:
    try:
        # markdown 코드블록 처리
        cleaned = _strip_markdown_code_block(raw_output)
        parsed = json.loads(cleaned)
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
        # markdown 코드블록 처리
        cleaned = _strip_markdown_code_block(raw_output)
        parsed = json.loads(cleaned)
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
