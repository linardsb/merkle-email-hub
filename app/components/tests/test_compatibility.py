# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for compatibility service methods and badge computation."""

from unittest.mock import AsyncMock, patch

import pytest

from app.components.exceptions import ComponentNotFoundError, ComponentQADataNotFoundError
from app.components.service import ComponentService
from app.components.tests.conftest import make_component, make_version


@pytest.fixture
def service() -> ComponentService:
    mock_db = AsyncMock()
    svc = ComponentService(mock_db)
    svc.repository = AsyncMock()
    return svc


# ── _compute_badge ──


def test_compute_badge_full():
    assert ComponentService._compute_badge({"a": "full", "b": "full"}) == "full"


def test_compute_badge_partial():
    assert ComponentService._compute_badge({"a": "full", "b": "partial"}) == "partial"


def test_compute_badge_issues():
    assert ComponentService._compute_badge({"a": "full", "b": "none"}) == "issues"


def test_compute_badge_none_data():
    assert ComponentService._compute_badge(None) is None


def test_compute_badge_empty_dict():
    assert ComponentService._compute_badge({}) is None


# ── get_compatibility ──


async def test_get_compatibility_no_qa_data(service):
    """Component with no QA runs → raises not found."""
    component = make_component(id=1)
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_latest_compatibility = AsyncMock(return_value=None)

    with pytest.raises(ComponentQADataNotFoundError, match="No QA compatibility data"):
        await service.get_compatibility(1)


async def test_get_compatibility_returns_response(service):
    """Component with QA data → correct compatibility response."""
    version = make_version(id=1, component_id=1, version_number=2)
    component = make_component(id=1, name="CTA Button")
    component.versions = [version]

    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_latest_compatibility = AsyncMock(
        return_value={"gmail_web": "full", "outlook_2019": "none"}
    )

    with patch("app.knowledge.ontology.registry.load_ontology") as mock_onto:
        from unittest.mock import MagicMock

        mock_client_1 = MagicMock()
        mock_client_1.name = "Gmail (Web)"
        mock_client_1.platform = "webmail"
        mock_client_2 = MagicMock()
        mock_client_2.name = "Outlook 2019"
        mock_client_2.platform = "desktop"

        mock_registry = MagicMock()

        def get_client_side_effect(cid: str) -> MagicMock | None:
            if cid == "gmail_web":
                return mock_client_1
            if cid == "outlook_2019":
                return mock_client_2
            return None

        mock_registry.get_client = get_client_side_effect
        mock_onto.return_value = mock_registry

        result = await service.get_compatibility(1)

    assert result.component_id == 1
    assert result.component_name == "CTA Button"
    assert result.full_count == 1
    assert result.none_count == 1
    assert len(result.clients) == 2


# ── run_qa_for_version ──


async def test_run_qa_for_version_not_found(service):
    """Non-existent version → raises not found."""
    component = make_component(id=1)
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_version = AsyncMock(return_value=None)

    with pytest.raises(ComponentNotFoundError, match="Version 5 not found"):
        await service.run_qa_for_version(1, 5)


# ── get_component with badge ──


async def test_get_component_includes_badge(service):
    """get_component populates compatibility_badge from latest QA result."""
    component = make_component(id=1, name="Header")
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_latest_version_number = AsyncMock(return_value=2)
    service.repository.get_latest_compatibility = AsyncMock(
        return_value={"gmail_web": "full", "outlook_2019": "partial"}
    )

    result = await service.get_component(1)
    assert result.compatibility_badge == "partial"


async def test_get_component_no_badge_without_qa(service):
    """get_component without QA data has no badge."""
    component = make_component(id=1, name="Header")
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_latest_version_number = AsyncMock(return_value=1)
    service.repository.get_latest_compatibility = AsyncMock(return_value=None)

    result = await service.get_component(1)
    assert result.compatibility_badge is None


# ── list_components with badges ──


async def test_list_components_includes_badges(service):
    """list_components populates compatibility_badge from batch QA data."""
    comp1 = make_component(id=1, name="Header")
    comp2 = make_component(id=2, name="Footer")

    service.repository.list = AsyncMock(return_value=[comp1, comp2])
    service.repository.count = AsyncMock(return_value=2)
    service.repository.get_latest_compatibility_batch = AsyncMock(
        return_value={
            1: {"gmail_web": "full", "outlook_2019": "full"},
            2: {"gmail_web": "full", "outlook_2019": "none"},
        }
    )
    service.repository.get_latest_version_compatibility_batch = AsyncMock(return_value={})

    from app.shared.schemas import PaginationParams

    result = await service.list_components(PaginationParams(page=1, page_size=20))

    assert result.items[0].compatibility_badge == "full"
    assert result.items[1].compatibility_badge == "issues"


async def test_list_components_no_qa_data(service):
    """list_components without QA data has no badge."""
    comp1 = make_component(id=1, name="Header")
    service.repository.list = AsyncMock(return_value=[comp1])
    service.repository.count = AsyncMock(return_value=1)
    service.repository.get_latest_compatibility_batch = AsyncMock(return_value={})
    service.repository.get_latest_version_compatibility_batch = AsyncMock(return_value={})

    from app.shared.schemas import PaginationParams

    result = await service.list_components(PaginationParams(page=1, page_size=20))

    assert result.items[0].compatibility_badge is None
