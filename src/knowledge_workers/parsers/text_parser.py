import aiofiles

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset({"text/plain", ".txt"})


class TextParser(BaseParser):
    """Parser for plain text files."""

    async def parse(self, file_path: str) -> str:
        """Read and return the full text content of a file."""
        async with aiofiles.open(file_path) as f:
            return await f.read()

    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        return content_type in SUPPORTED_CONTENT_TYPES
