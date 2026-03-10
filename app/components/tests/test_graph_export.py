# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for component graph export to Cognee."""

from unittest.mock import AsyncMock, MagicMock

from app.components.graph_export import export_component_documents
from app.components.tests.conftest import make_component, make_version


def _mock_db_with_components(components: list[object]) -> AsyncMock:
    """Create a mock DB session that returns the given components."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = components
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    return mock_db


async def test_export_empty_db():
    """No components → empty list."""
    mock_db = _mock_db_with_components([])
    docs = await export_component_documents(mock_db)
    assert docs == []


async def test_export_component_with_compatibility():
    """Component with compatibility data → structured document with compatibility section."""
    version = make_version(
        id=1,
        component_id=1,
        version_number=1,
        compatibility={"gmail_web": "full", "outlook_2019": "none"},
    )
    comp = make_component(id=1, name="CTA Button", slug="cta-button", category="action")
    comp.versions = [version]

    mock_db = _mock_db_with_components([comp])
    docs = await export_component_documents(mock_db)

    assert len(docs) == 1
    dataset, text = docs[0]
    assert dataset == "email_components"
    assert "CTA Button" in text
    assert "## Client Compatibility" in text


async def test_export_component_no_compatibility():
    """Component without QA data → basic document without compatibility section."""
    version = make_version(id=1, component_id=1, version_number=1, compatibility=None)
    comp = make_component(id=1, name="Header", slug="header")
    comp.versions = [version]

    mock_db = _mock_db_with_components([comp])
    docs = await export_component_documents(mock_db)

    assert len(docs) == 1
    _dataset, text = docs[0]
    assert "Header" in text
    assert "## Client Compatibility" not in text


async def test_export_skips_components_without_versions():
    """Components with no versions are skipped."""
    comp = make_component(id=1, name="Empty", slug="empty")
    comp.versions = []

    mock_db = _mock_db_with_components([comp])
    docs = await export_component_documents(mock_db)

    assert docs == []


async def test_dataset_name():
    """All component documents use 'email_components' dataset."""
    v1 = make_version(id=1, component_id=1, version_number=1)
    v2 = make_version(id=2, component_id=2, version_number=1)
    c1 = make_component(id=1, name="Header", slug="header")
    c1.versions = [v1]
    c2 = make_component(id=2, name="Footer", slug="footer")
    c2.versions = [v2]

    mock_db = _mock_db_with_components([c1, c2])
    docs = await export_component_documents(mock_db)

    assert len(docs) == 2
    assert all(dataset == "email_components" for dataset, _ in docs)
