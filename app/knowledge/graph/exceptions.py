"""Graph knowledge exceptions."""

from app.core.exceptions import AppError, ServiceUnavailableError


class GraphError(AppError):
    """Base error for graph knowledge operations."""


class GraphNotEnabledError(ServiceUnavailableError):
    """Raised when graph features are used but Cognee is disabled (503)."""


class GraphIngestionError(GraphError):
    """Raised when document ingestion into the graph fails (500)."""


class GraphSearchError(GraphError):
    """Raised when a graph search query fails (500)."""
