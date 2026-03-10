# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for QA bridge — component QA execution and compatibility extraction."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.components.qa_bridge import extract_compatibility, run_component_qa
from app.components.tests.conftest import make_version

# ── extract_compatibility ──


def test_extract_compatibility_clean_html():
    """HTML with no unsupported CSS → all clients 'full'."""
    html = "<table><tr><td>Hello</td></tr></table>"
    compat = extract_compatibility(html)
    assert len(compat) > 0
    assert all(v == "full" for v in compat.values())


def test_extract_compatibility_with_issues():
    """HTML using poorly-supported CSS → affected clients 'none' or 'partial'."""
    # display: flex is known to be unsupported in several email clients
    html = '<div style="display: flex;">Content</div>'
    compat = extract_compatibility(html)
    assert len(compat) > 0
    # At least some clients should not have full support
    levels = set(compat.values())
    assert levels != {"full"}, "Expected some clients to lack full support for display: flex"


def test_extract_compatibility_returns_all_clients():
    """Compatibility map should include an entry for every client in the ontology."""
    from app.knowledge.ontology.registry import load_ontology

    onto = load_ontology()
    html = "<table><tr><td>Hello</td></tr></table>"
    compat = extract_compatibility(html)
    assert set(compat.keys()) == {c.id for c in onto.clients}


# ── run_component_qa ──


async def test_run_component_qa_stores_result():
    """Full flow: creates QA result + ComponentQAResult + updates version.compatibility."""
    version = make_version(id=10, component_id=1, version_number=1)
    mock_db = AsyncMock()

    mock_qa_response = MagicMock()
    mock_qa_response.id = 42

    with patch("app.components.qa_bridge.QAEngineService") as mock_qa_cls:
        mock_qa_svc = AsyncMock()
        mock_qa_svc.run_checks.return_value = mock_qa_response
        mock_qa_cls.return_value = mock_qa_svc

        cqa = await run_component_qa(mock_db, version)

    assert cqa.component_version_id == 10
    assert cqa.qa_result_id == 42
    assert isinstance(cqa.compatibility, dict)
    assert len(cqa.compatibility) > 0
    # Version.compatibility should also be updated
    assert version.compatibility == cqa.compatibility
    mock_db.add.assert_called_once()
    assert mock_db.commit.await_count == 1  # single atomic commit for cqa + version


async def test_run_component_qa_links_qa_result():
    """Verifies the ComponentQAResult references the QA result ID from the engine."""
    version = make_version(id=20, component_id=2, version_number=3)
    mock_db = AsyncMock()

    mock_qa_response = MagicMock()
    mock_qa_response.id = 99

    with patch("app.components.qa_bridge.QAEngineService") as mock_qa_cls:
        mock_qa_svc = AsyncMock()
        mock_qa_svc.run_checks.return_value = mock_qa_response
        mock_qa_cls.return_value = mock_qa_svc

        cqa = await run_component_qa(mock_db, version)

    assert cqa.qa_result_id == 99
    assert cqa.component_version_id == 20
