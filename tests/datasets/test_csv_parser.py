import pytest

from src.datasets.csv_parser import parse_csv


class TestParseCsvSuccess:
    """정상적인 CSV 파싱 케이스"""

    def test_separates_input_data_and_expected_output(self):
        """input_data와 expected_output을 분리해야 한다."""
        csv_bytes = "msg,author,expected_output\n안녕,홍길동,인사 응답\n".encode()

        rows = parse_csv(csv_bytes)

        assert len(rows) == 1
        assert rows[0]["input_data"] == {"msg": "안녕", "author": "홍길동"}
        assert rows[0]["expected_output"] == "인사 응답"
        assert rows[0]["tags"] is None


class TestParseCsvValidation:
    """CSV 유효성 검사 케이스"""

    def test_raises_error_when_expected_output_column_missing(self):
        """expected_output 컬럼이 없으면 에러를 발생시켜야 한다."""
        csv_bytes = "msg,author\n안녕,홍길동\n".encode()

        with pytest.raises(ValueError, match="expected_output"):
            parse_csv(csv_bytes)

    def test_raises_error_when_expected_output_is_empty(self):
        """expected_output이 빈 행이 있으면 에러를 발생시켜야 한다."""
        csv_bytes = "msg,expected_output\n안녕,응답\n반가워,\n".encode()

        with pytest.raises(ValueError) as exc_info:
            parse_csv(csv_bytes)

        errors = exc_info.value.args[0]
        assert any(e["row"] == 3 for e in errors)

    def test_skips_empty_rows(self):
        """빈 줄은 건너뛰어야 한다."""
        csv_bytes = "msg,expected_output\n안녕,응답\n\n반가워,응답2\n".encode()

        rows = parse_csv(csv_bytes)

        assert len(rows) == 2

    def test_raises_error_on_duplicate_headers(self):
        """중복 헤더가 있으면 에러를 발생시켜야 한다."""
        csv_bytes = "msg,msg,expected_output\na,b,응답\n".encode()

        with pytest.raises(ValueError, match="중복"):
            parse_csv(csv_bytes)

    def test_parses_tags_as_comma_separated_list(self):
        """tags 컬럼을 쉼표로 분리하여 배열로 변환해야 한다."""
        csv_bytes = 'msg,expected_output,tags\n안녕,응답,"인사,기본"\n'.encode()

        rows = parse_csv(csv_bytes)

        assert rows[0]["tags"] == ["인사", "기본"]

    def test_returns_none_for_empty_tags(self):
        """tags가 비어있으면 None을 반환해야 한다."""
        csv_bytes = "msg,expected_output,tags\n안녕,응답,\n".encode()

        rows = parse_csv(csv_bytes)

        assert rows[0]["tags"] is None


class TestParseCsvEncoding:
    """인코딩 처리 케이스"""

    def test_parses_euc_kr_encoded_csv(self):
        """EUC-KR 인코딩 CSV를 파싱해야 한다."""
        csv_bytes = "msg,expected_output\n안녕하세요,응답\n".encode("euc-kr")

        rows = parse_csv(csv_bytes)

        assert rows[0]["input_data"] == {"msg": "안녕하세요"}

    def test_parses_utf8_bom_csv(self):
        """UTF-8 BOM이 있는 CSV를 파싱해야 한다."""
        csv_bytes = "\ufeffmsg,expected_output\n안녕,응답\n".encode("utf-8-sig")

        rows = parse_csv(csv_bytes)

        assert "msg" in rows[0]["input_data"]
