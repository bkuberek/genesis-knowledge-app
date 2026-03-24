import docx

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    }
)


class DocxParser(BaseParser):
    """Parser for DOCX files using python-docx."""

    async def parse(self, file_path: str) -> str:
        """Parse a DOCX file and return text from all paragraphs."""
        document = docx.Document(file_path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)

    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        return content_type in SUPPORTED_CONTENT_TYPES
