import tempfile

import pytest

from knowledge_workers.parsers import get_parser
from knowledge_workers.parsers.csv_parser import (
    CsvParser,
    _coerce_value,
    _detect_name_column,
    _infer_entity_type,
)
from knowledge_workers.parsers.docx_parser import DocxParser
from knowledge_workers.parsers.pdf_parser import PdfParser
from knowledge_workers.parsers.text_parser import TextParser
from knowledge_workers.parsers.url_parser import UrlParser


class TestCsvParser:
    def test_supports_text_csv_content_type(self):
        parser = CsvParser()
        assert parser.supports("text/csv") is True

    def test_supports_application_csv_content_type(self):
        parser = CsvParser()
        assert parser.supports("application/csv") is True

    def test_supports_csv_extension(self):
        parser = CsvParser()
        assert parser.supports(".csv") is True

    def test_rejects_unsupported_content_type(self):
        parser = CsvParser()
        assert parser.supports("application/pdf") is False


class TestCsvParserExtractEntities:
    """Tests for direct CSV-to-entity extraction."""

    def _write_csv(self, content: str) -> str:
        """Write CSV content to a temp file and return its path."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
        ) as tmp:
            tmp.write(content)
            return tmp.name

    def test_extracts_entities_from_simple_csv(self):
        csv_content = "company_name,industry,revenue\nAcme Corp,tech,5000\nBeta Inc,finance,3000\n"
        path = self._write_csv(csv_content)
        parser = CsvParser()
        entities = parser.extract_entities(path)

        assert len(entities) == 2
        assert entities[0]["name"] == "Acme Corp"
        assert entities[0]["type"] == "company"
        assert entities[0]["properties"]["industry"] == "tech"
        assert entities[0]["properties"]["revenue"] == 5000

    def test_detects_company_name_column(self):
        csv_content = "company_name,arr_thousands\nSignalTech,816\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert entities[0]["name"] == "SignalTech"

    def test_falls_back_to_first_column_for_name(self):
        csv_content = "label,value\nfoo,42\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert entities[0]["name"] == "foo"

    def test_preserves_numeric_types(self):
        csv_content = "name,count,rate\nWidget,100,3.14\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        props = entities[0]["properties"]
        assert isinstance(props["count"], int)
        assert isinstance(props["rate"], float)

    def test_empty_csv_returns_no_entities(self):
        csv_content = "name,value\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert entities == []

    def test_skips_rows_with_empty_name(self):
        csv_content = "name,value\nfoo,1\n,2\nbar,3\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert len(entities) == 2
        names = [e["name"] for e in entities]
        assert "foo" in names
        assert "bar" in names

    def test_infers_record_type_for_generic_columns(self):
        csv_content = "id,status,score\nA,active,99\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert entities[0]["type"] == "record"

    def test_handles_nan_values_as_none(self):
        csv_content = "name,optional\nfoo,\n"
        path = self._write_csv(csv_content)
        entities = CsvParser().extract_entities(path)

        assert entities[0]["properties"]["optional"] is None


class TestDetectNameColumn:
    def test_detects_company_name(self):
        assert _detect_name_column(["company_name", "revenue"]) == "company_name"

    def test_detects_name_column(self):
        assert _detect_name_column(["id", "name", "age"]) == "name"

    def test_detects_title_column(self):
        assert _detect_name_column(["title", "author"]) == "title"

    def test_falls_back_to_first_column(self):
        assert _detect_name_column(["identifier", "value"]) == "identifier"


class TestInferEntityType:
    def test_infers_company_from_column_names(self):
        assert _infer_entity_type(["company_name", "revenue"]) == "company"

    def test_infers_person_from_column_names(self):
        assert _infer_entity_type(["person_id", "age"]) == "person"

    def test_returns_record_for_unknown(self):
        assert _infer_entity_type(["id", "value", "score"]) == "record"


class TestCoerceValue:
    def test_preserves_string(self):
        assert _coerce_value("hello") == "hello"

    def test_strips_string_whitespace(self):
        assert _coerce_value("  padded  ") == "padded"

    def test_converts_nan_to_none(self):
        import numpy as np

        assert _coerce_value(float("nan")) is None
        assert _coerce_value(np.nan) is None

    def test_preserves_int(self):
        import numpy as np

        assert _coerce_value(np.int64(42)) == 42
        assert isinstance(_coerce_value(np.int64(42)), int)

    def test_preserves_float(self):
        import numpy as np

        result = _coerce_value(np.float64(3.14))
        assert isinstance(result, float)
        assert abs(result - 3.14) < 0.001


class TestPdfParser:
    def test_supports_application_pdf_content_type(self):
        parser = PdfParser()
        assert parser.supports("application/pdf") is True

    def test_supports_pdf_extension(self):
        parser = PdfParser()
        assert parser.supports(".pdf") is True

    def test_rejects_unsupported_content_type(self):
        parser = PdfParser()
        assert parser.supports("text/csv") is False


class TestDocxParser:
    def test_supports_docx_mime_type(self):
        parser = DocxParser()
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert parser.supports(mime) is True

    def test_supports_docx_extension(self):
        parser = DocxParser()
        assert parser.supports(".docx") is True

    def test_rejects_unsupported_content_type(self):
        parser = DocxParser()
        assert parser.supports("text/plain") is False


class TestTextParser:
    def test_supports_text_plain_content_type(self):
        parser = TextParser()
        assert parser.supports("text/plain") is True

    def test_supports_txt_extension(self):
        parser = TextParser()
        assert parser.supports(".txt") is True

    def test_rejects_unsupported_content_type(self):
        parser = TextParser()
        assert parser.supports("application/pdf") is False


class TestUrlParser:
    def test_supports_url_content_type(self):
        parser = UrlParser()
        assert parser.supports("url") is True

    def test_supports_text_url_content_type(self):
        parser = UrlParser()
        assert parser.supports("text/url") is True

    def test_supports_url_extension(self):
        parser = UrlParser()
        assert parser.supports(".url") is True

    def test_rejects_unsupported_content_type(self):
        parser = UrlParser()
        assert parser.supports("text/plain") is False


class TestGetParser:
    def test_returns_csv_parser_for_csv_content_type(self):
        parser = get_parser("text/csv")
        assert isinstance(parser, CsvParser)

    def test_returns_pdf_parser_for_pdf_content_type(self):
        parser = get_parser("application/pdf")
        assert isinstance(parser, PdfParser)

    def test_returns_text_parser_for_text_content_type(self):
        parser = get_parser("text/plain")
        assert isinstance(parser, TextParser)

    def test_returns_docx_parser_for_docx_content_type(self):
        parser = get_parser(".docx")
        assert isinstance(parser, DocxParser)

    def test_returns_url_parser_for_url_content_type(self):
        parser = get_parser("url")
        assert isinstance(parser, UrlParser)

    def test_raises_value_error_for_unknown_content_type(self):
        with pytest.raises(ValueError, match="No parser available"):
            get_parser("application/unknown")
