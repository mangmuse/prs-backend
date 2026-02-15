from src.prompts.models import OutputSchemaType
from src.runs.evaluator.format_layer import _strip_markdown_code_block, check_format


class TestStripMarkdownCodeBlock:
    """Markdown 코드블록 제거 테스트"""

    def test_strip_markdown_json_code_block(self):
        """```json {...} ``` 감싸진 JSON에서 내용만 추출"""
        text = '```json\n{"key": "value"}\n```'

        result = _strip_markdown_code_block(text)

        assert result == '{"key": "value"}'

    def test_strip_markdown_code_block_without_language_tag(self):
        """``` {...} ``` 언어 태그 없는 코드블록에서 내용만 추출"""
        text = '```\n{"key": "value"}\n```'

        result = _strip_markdown_code_block(text)

        assert result == '{"key": "value"}'

    def test_strip_markdown_code_block_no_block_returns_original(self):
        """코드블록 없으면 원본 반환"""
        text = '{"key": "value"}'

        result = _strip_markdown_code_block(text)

        assert result == '{"key": "value"}'


class TestCheckFormatEdgeCases:
    """Format Layer 엣지 케이스 테스트"""

    def test_json_object_empty_string_fails(self):
        """빈 문자열 입력 시 JSON Object 파싱 실패"""
        result = check_format(
            raw_output="",
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output=None,
        )

        assert result.passed is False

    def test_json_array_empty_string_fails(self):
        """빈 문자열 입력 시 JSON Array 파싱 실패"""
        result = check_format(
            raw_output="",
            output_schema=OutputSchemaType.JSON_ARRAY,
            expected_output=None,
        )

        assert result.passed is False

    def test_json_object_whitespace_only_fails(self):
        """공백만 입력 시 JSON Object 파싱 실패"""
        result = check_format(
            raw_output="   ",
            output_schema=OutputSchemaType.JSON_OBJECT,
            expected_output=None,
        )

        assert result.passed is False

    def test_label_none_expected_output_fails(self):
        """expected_output=None이면 Label 불일치 실패"""
        result = check_format(
            raw_output="TRUE",
            output_schema=OutputSchemaType.LABEL,
            expected_output=None,
        )

        assert result.passed is False


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
