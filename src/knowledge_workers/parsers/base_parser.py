import abc


class BaseParser(abc.ABC):
    """Abstract base class for document parsers."""

    @abc.abstractmethod
    async def parse(self, file_path: str) -> str:
        """Parse a file and return its text content."""
        ...

    @abc.abstractmethod
    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        ...
