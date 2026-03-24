"""Document parsers for various file formats."""

from knowledge_workers.parsers.base_parser import BaseParser
from knowledge_workers.parsers.csv_parser import CsvParser
from knowledge_workers.parsers.docx_parser import DocxParser
from knowledge_workers.parsers.pdf_parser import PdfParser
from knowledge_workers.parsers.text_parser import TextParser
from knowledge_workers.parsers.url_parser import UrlParser

_PARSERS: list[BaseParser] = [
    CsvParser(),
    PdfParser(),
    DocxParser(),
    TextParser(),
    UrlParser(),
]


def get_parser(content_type: str) -> BaseParser:
    """Get the appropriate parser for a content type."""
    for parser in _PARSERS:
        if parser.supports(content_type):
            return parser
    raise ValueError(f"No parser available for content type: {content_type}")


__all__ = [
    "BaseParser",
    "CsvParser",
    "DocxParser",
    "PdfParser",
    "TextParser",
    "UrlParser",
    "get_parser",
]
