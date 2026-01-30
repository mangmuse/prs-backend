from src.prompts.models import OutputSchemaType
from src.runs.evaluator.format_layer import check_format


class TestCheckFormatJsonObject:
    """JSON Object 스키마 검증 테스트"""

    def test_valid_json_object(self):
        """유효한 JSON Object는 통과해야 함"""
        raw_output = '{"verdict": "TRUE", "confidence": 0.9}'

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output=None,
        )

        assert result.passed is True
        assert result.parsed_output == {"verdict": "TRUE", "confidence": 0.9}

    def test_invalid_json_syntax(self):
        """잘못된 JSON 문법은 실패"""
        raw_output = "{invalid json}"

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output=None,
        )

        assert result.passed is False
        assert result.parsed_output is None

    def test_non_object_type_fails(self):
        """JSON Object가 아닌 타입은 실패"""
        raw_output = '["item1", "item2"]'

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output=None,
        )

        assert result.passed is False


class TestCheckFormatJsonArray:
    """JSON Array 스키마 검증 테스트"""

    def test_valid_json_array(self):
        """유효한 JSON Array는 통과"""
        raw_output = '["item1", "item2", "item3"]'

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.JSON_ARRAY,
            expected_output=None,
        )

        assert result.passed is True
        assert result.parsed_output == ["item1", "item2", "item3"]

    def test_non_array_type_fails(self):
        """JSON Array가 아닌 타입은 실패"""
        raw_output = '{"key": "value"}'

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.JSON_ARRAY,
            expected_output=None,
        )

        assert result.passed is False


class TestCheckFormatLabel:
    """Label 스키마 검증 테스트"""

    def test_exact_match_passes(self):
        """정확히 일치하면 통과"""
        raw_output = "TRUE"

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.LABEL,
            expected_output="TRUE",
        )

        assert result.passed is True
        assert result.parsed_output == "TRUE"

    def test_case_sensitive_fails(self):
        """대소문자 다르면 실패 (case-sensitive)"""
        raw_output = "true"

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.LABEL,
            expected_output="TRUE",
        )

        assert result.passed is False


class TestCheckFormatFreeform:
    """Freeform 스키마 검증 테스트"""

    def test_always_passes(self):
        """Freeform은 항상 통과"""
        raw_output = "아무 형식이나 상관없음"

        result = check_format(
            raw_output=raw_output,
            output_schema=OutputSchemaType.FREEFORM,
            expected_output=None,
        )

        assert result.passed is True
        assert result.parsed_output == "아무 형식이나 상관없음"
