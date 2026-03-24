class KnowledgeError(Exception):
    """Base exception for the Knowledge application."""


class DocumentProcessingError(KnowledgeError):
    """Raised when document processing fails."""


class EntityResolutionError(KnowledgeError):
    """Raised when entity resolution fails."""


class AuthenticationError(KnowledgeError):
    """Raised when authentication fails."""


class AuthorizationError(KnowledgeError):
    """Raised when authorization fails."""
