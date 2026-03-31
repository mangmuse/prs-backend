from src.datasets.csv_exporter import rows_to_csv
from src.datasets.csv_parser import parse_csv


class TestRowsToCsvSuccess:
    """정상적인 CSV 생성 케이스"""

    def test_generates_csv_with_input_data_columns(self):
        """input_data의 key를 개별 CSV 열로 변환해야 한다."""
        rows = [
            {
                "input_data": {"question": "안녕", "context": "인사"},
                "expected_output": "응답",
                "tags": None,
            }
        ]

        result = rows_to_csv(rows)

        lines = result.strip().split("\n")
        assert lines[0] == "question,context,expected_output,tags"
        assert "안녕" in lines[1]
        assert "인사" in lines[1]
        assert "응답" in lines[1]

    def test_joins_tags_with_comma(self):
        """tags 배열을 쉼표로 결합해야 한다."""
        rows = [
            {
                "input_data": {"msg": "테스트"},
                "expected_output": "응답",
                "tags": ["인사", "기본"],
            }
        ]

        result = rows_to_csv(rows)

        lines = result.strip().split("\n")
        assert '"인사,기본"' in lines[1] or "인사,기본" in lines[1]

    def test_returns_header_only_for_empty_rows(self):
        """빈 행 목록이면 헤더만 반환해야 한다."""
        result = rows_to_csv([])

        assert result.strip() == "expected_output,tags"

    def test_unions_different_input_keys(self):
        """행마다 다른 input_data key가 있으면 합집합으로 열을 생성해야 한다."""
        rows = [
            {"input_data": {"a": "1"}, "expected_output": "o1", "tags": None},
            {"input_data": {"a": "2", "b": "3"}, "expected_output": "o2", "tags": None},
        ]

        result = rows_to_csv(rows)

        lines = result.strip().split("\n")
        assert "a" in lines[0]
        assert "b" in lines[0]
        assert len(lines) == 3


class TestCsvRoundTrip:
    """export → import 라운드트립 검증"""

    def test_exported_csv_can_be_reimported(self):
        """export한 CSV를 다시 import하면 동일한 데이터여야 한다."""
        original_rows = [
            {
                "input_data": {"question": "한국의 수도는?", "context": "지리"},
                "expected_output": "서울",
                "tags": ["지리", "기본"],
            },
            {
                "input_data": {"question": "1+1은?", "context": "수학"},
                "expected_output": "2",
                "tags": None,
            },
        ]

        csv_text = rows_to_csv(original_rows)
        reimported = parse_csv(csv_text.encode("utf-8"))

        assert len(reimported) == len(original_rows)
        for orig, reimp in zip(original_rows, reimported, strict=True):
            assert reimp["input_data"] == orig["input_data"]
            assert reimp["expected_output"] == orig["expected_output"]
            assert reimp["tags"] == orig["tags"]
