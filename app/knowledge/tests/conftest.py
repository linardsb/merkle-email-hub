"""Test fixtures and factory functions for knowledge base tests."""

from app.knowledge.schemas import DocumentUpload, SearchRequest, TagCreate


def make_upload(
    *,
    domain: str = "general",
    language: str = "en",
    title: str | None = None,
    description: str | None = None,
    metadata_json: str | None = None,
) -> DocumentUpload:
    """Create a DocumentUpload instance for testing.

    Args:
        domain: Knowledge domain.
        language: Document language code.
        title: Optional document title.
        description: Optional document description.
        metadata_json: Optional JSON metadata.

    Returns:
        DocumentUpload instance.
    """
    return DocumentUpload(
        domain=domain,
        language=language,
        title=title,
        description=description,
        metadata_json=metadata_json,
    )


def make_search_request(
    *,
    query: str = "test query",
    domain: str | None = None,
    language: str | None = None,
    limit: int = 10,
) -> SearchRequest:
    """Create a SearchRequest instance for testing.

    Args:
        query: Search query text.
        domain: Optional domain filter.
        language: Optional language filter.
        limit: Maximum results.

    Returns:
        SearchRequest instance.
    """
    return SearchRequest(
        query=query,
        domain=domain,
        language=language,
        limit=limit,
    )


def make_tag_create(*, name: str = "test-tag") -> TagCreate:
    """Create a TagCreate instance for testing.

    Args:
        name: Tag name.

    Returns:
        TagCreate instance.
    """
    return TagCreate(name=name)
