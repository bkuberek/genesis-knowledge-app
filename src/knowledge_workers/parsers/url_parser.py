import httpx
import trafilatura

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset({"text/url", "url", ".url"})


class UrlParser(BaseParser):
    """Parser for web URLs using trafilatura for content extraction."""

    async def parse(self, file_path: str) -> str:
        """Fetch a URL and extract its main text content.

        The file_path parameter is actually a URL for this parser.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(file_path, follow_redirects=True)
            response.raise_for_status()
        extracted = trafilatura.extract(response.text)
        return extracted or ""

    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        return content_type in SUPPORTED_CONTENT_TYPES
