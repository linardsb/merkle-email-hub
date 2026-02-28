# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
"""Unit tests for ItemService business logic."""

from unittest.mock import AsyncMock

import pytest

from app.example.exceptions import ItemAlreadyExistsError, ItemNotFoundError
from app.example.schemas import ItemCreate, ItemUpdate
from app.example.service import ItemService
from app.example.tests.conftest import make_item
from app.shared.schemas import PaginationParams


@pytest.fixture
def service() -> ItemService:
    mock_db = AsyncMock()
    svc = ItemService(mock_db)
    svc.repository = AsyncMock()
    return svc


async def test_get_item_success(service):
    item = make_item(id=1, name="Test Item")
    service.repository.get = AsyncMock(return_value=item)

    result = await service.get_item(1)
    assert result.id == 1
    assert result.name == "Test Item"
    service.repository.get.assert_awaited_once_with(1)


async def test_get_item_not_found(service):
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ItemNotFoundError, match="Item 999 not found"):
        await service.get_item(999)


async def test_list_items(service):
    items = [
        make_item(id=1, name="Alpha"),
        make_item(id=2, name="Beta"),
    ]
    service.repository.list = AsyncMock(return_value=items)
    service.repository.count = AsyncMock(return_value=2)

    pagination = PaginationParams(page=1, page_size=20)
    result = await service.list_items(pagination)

    assert len(result.items) == 2
    assert result.total == 2
    assert result.page == 1


async def test_create_item_success(service):
    data = ItemCreate(name="New Item", description="A new item")
    created = make_item(id=10, name="New Item", description="A new item")
    service.repository.get_by_name = AsyncMock(return_value=None)
    service.repository.create = AsyncMock(return_value=created)

    result = await service.create_item(data)
    assert result.id == 10
    assert result.name == "New Item"


async def test_create_item_duplicate(service):
    data = ItemCreate(name="Existing Item")
    existing = make_item(id=1, name="Existing Item")
    service.repository.get_by_name = AsyncMock(return_value=existing)

    with pytest.raises(ItemAlreadyExistsError, match="already exists"):
        await service.create_item(data)


async def test_update_item_success(service):
    item = make_item(id=1, name="Old Name")
    updated = make_item(id=1, name="New Name")
    data = ItemUpdate(name="New Name")

    service.repository.get = AsyncMock(return_value=item)
    service.repository.get_by_name = AsyncMock(return_value=None)
    service.repository.update = AsyncMock(return_value=updated)

    result = await service.update_item(1, data)
    assert result.name == "New Name"


async def test_update_item_not_found(service):
    service.repository.get = AsyncMock(return_value=None)
    data = ItemUpdate(name="New Name")

    with pytest.raises(ItemNotFoundError, match="Item 999 not found"):
        await service.update_item(999, data)


async def test_update_item_duplicate_name(service):
    item = make_item(id=1, name="Original")
    existing = make_item(id=2, name="Taken Name")
    data = ItemUpdate(name="Taken Name")

    service.repository.get = AsyncMock(return_value=item)
    service.repository.get_by_name = AsyncMock(return_value=existing)

    with pytest.raises(ItemAlreadyExistsError, match="already exists"):
        await service.update_item(1, data)


async def test_delete_item_success(service):
    item = make_item(id=1)
    service.repository.get = AsyncMock(return_value=item)
    service.repository.delete = AsyncMock()

    await service.delete_item(1)
    service.repository.delete.assert_awaited_once_with(item)


async def test_delete_item_not_found(service):
    service.repository.get = AsyncMock(return_value=None)

    with pytest.raises(ItemNotFoundError, match="Item 999 not found"):
        await service.delete_item(999)
