# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for ComponentService business logic."""

from unittest.mock import AsyncMock

import pytest

from app.components.exceptions import ComponentAlreadyExistsError, ComponentNotFoundError
from app.components.schemas import ComponentCreate, ComponentUpdate, VersionCreate
from app.components.service import ComponentService
from app.components.tests.conftest import make_component, make_version
from app.shared.schemas import PaginationParams


@pytest.fixture
def service() -> ComponentService:
    mock_db = AsyncMock()
    svc = ComponentService(mock_db)
    svc.repository = AsyncMock()
    return svc


# ── Component CRUD ──


async def test_get_component_success(service):
    component = make_component(id=1, name="Header")
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_latest_version_number = AsyncMock(return_value=2)
    service.repository.get_latest_compatibility = AsyncMock(return_value=None)

    result = await service.get_component(1)
    assert result.id == 1
    assert result.name == "Header"
    assert result.latest_version == 2
    service.repository.get.assert_awaited_once_with(1)


async def test_get_component_not_found(service):
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ComponentNotFoundError, match="Component 999 not found"):
        await service.get_component(999)


async def test_list_components(service):
    components = [
        make_component(id=1, name="Header"),
        make_component(id=2, name="Footer"),
    ]
    service.repository.list = AsyncMock(return_value=components)
    service.repository.count = AsyncMock(return_value=2)

    pagination = PaginationParams(page=1, page_size=20)
    result = await service.list_components(pagination)

    assert len(result.items) == 2
    assert result.total == 2
    assert result.page == 1


async def test_list_components_with_category_filter(service):
    components = [make_component(id=1, name="Header", category="structure")]
    service.repository.list = AsyncMock(return_value=components)
    service.repository.count = AsyncMock(return_value=1)

    pagination = PaginationParams(page=1, page_size=20)
    result = await service.list_components(pagination, category="structure")

    assert len(result.items) == 1
    service.repository.list.assert_awaited_once_with(
        offset=0, limit=20, category="structure", search=None
    )


async def test_create_component_success(service):
    data = ComponentCreate(
        name="New Component",
        slug="new-component",
        html_source="<table><tr><td>Hello</td></tr></table>",
    )
    created = make_component(id=10, name="New Component", slug="new-component")
    service.repository.get_by_slug = AsyncMock(return_value=None)
    service.repository.create = AsyncMock(return_value=created)

    result = await service.create_component(data, user_id=1)
    assert result.id == 10
    assert result.name == "New Component"
    assert result.latest_version == 1


async def test_create_component_duplicate_slug(service):
    data = ComponentCreate(
        name="Duplicate",
        slug="existing-slug",
        html_source="<table><tr><td>Hello</td></tr></table>",
    )
    existing = make_component(id=1, slug="existing-slug")
    service.repository.get_by_slug = AsyncMock(return_value=existing)

    with pytest.raises(ComponentAlreadyExistsError, match="already exists"):
        await service.create_component(data, user_id=1)


async def test_create_component_sanitizes_html(service):
    """Verify XSS vectors are stripped from HTML before storage."""
    malicious_html = '<table><tr><td><script>alert("xss")</script>Clean</td></tr></table>'
    data = ComponentCreate(
        name="Sanitized",
        slug="sanitized",
        html_source=malicious_html,
    )
    created = make_component(id=11, name="Sanitized", slug="sanitized")
    service.repository.get_by_slug = AsyncMock(return_value=None)
    service.repository.create = AsyncMock(return_value=created)

    await service.create_component(data, user_id=1)

    # Check that the HTML passed to repository has script tags removed
    call_args = service.repository.create.call_args
    passed_data = call_args[0][0]
    assert "<script>" not in passed_data.html_source
    assert "Clean" in passed_data.html_source


async def test_update_component_success(service):
    component = make_component(id=1, name="Old Name")
    updated = make_component(id=1, name="New Name")
    data = ComponentUpdate(name="New Name")

    service.repository.get = AsyncMock(return_value=component)
    service.repository.update = AsyncMock(return_value=updated)

    result = await service.update_component(1, data)
    assert result.name == "New Name"


async def test_update_component_not_found(service):
    service.repository.get = AsyncMock(return_value=None)
    data = ComponentUpdate(name="New Name")

    with pytest.raises(ComponentNotFoundError, match="Component 999 not found"):
        await service.update_component(999, data)


async def test_delete_component_success(service):
    component = make_component(id=1)
    service.repository.get = AsyncMock(return_value=component)
    service.repository.delete = AsyncMock()

    await service.delete_component(1)
    service.repository.delete.assert_awaited_once_with(component)


async def test_delete_component_not_found(service):
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ComponentNotFoundError, match="Component 999 not found"):
        await service.delete_component(999)


# ── Versioning ──


async def test_create_version_success(service):
    component = make_component(id=1)
    version = make_version(id=5, component_id=1, version_number=2)
    data = VersionCreate(html_source="<table><tr><td>v2</td></tr></table>", changelog="Updated")

    service.repository.get = AsyncMock(return_value=component)
    service.repository.create_version = AsyncMock(return_value=version)

    result = await service.create_version(1, data, user_id=1)
    assert result.version_number == 2
    assert result.component_id == 1


async def test_create_version_sanitizes_html(service):
    """Verify XSS vectors are stripped from version HTML before storage."""
    component = make_component(id=1)
    version = make_version(id=6, component_id=1, version_number=2)
    malicious_html = '<table onclick="steal()"><tr><td>Content</td></tr></table>'
    data = VersionCreate(html_source=malicious_html)

    service.repository.get = AsyncMock(return_value=component)
    service.repository.create_version = AsyncMock(return_value=version)

    await service.create_version(1, data, user_id=1)

    call_args = service.repository.create_version.call_args
    passed_data = call_args[0][1]
    assert "onclick" not in passed_data.html_source
    assert "Content" in passed_data.html_source


async def test_create_version_component_not_found(service):
    data = VersionCreate(html_source="<table><tr><td>test</td></tr></table>")
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ComponentNotFoundError, match="Component 999 not found"):
        await service.create_version(999, data, user_id=1)


async def test_list_versions_success(service):
    component = make_component(id=1)
    versions = [
        make_version(id=2, version_number=2),
        make_version(id=1, version_number=1),
    ]
    service.repository.get = AsyncMock(return_value=component)
    service.repository.get_versions = AsyncMock(return_value=versions)

    result = await service.list_versions(1)
    assert len(result) == 2
    assert result[0].version_number == 2


async def test_list_versions_component_not_found(service):
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ComponentNotFoundError, match="Component 999 not found"):
        await service.list_versions(999)
