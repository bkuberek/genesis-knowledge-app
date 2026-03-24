import pytest

from knowledge_workers.parsers import get_parser
from knowledge_workers.parsers.csv_parser import CsvParser
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
