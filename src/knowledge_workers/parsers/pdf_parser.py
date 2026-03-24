import pdfplumber

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset({"application/pdf", ".pdf"})


class PdfParser(BaseParser):
    """Parser for PDF files using pdfplumber."""

    async def parse(self, file_path: str) -> str:
        """Parse a PDF file and return extracted text from all pages."""
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)

    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        return content_type in SUPPORTED_CONTENT_TYPES
