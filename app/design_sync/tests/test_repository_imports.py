"""Tests for design import repository CRUD operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.design_sync.models import DesignImport, DesignImportAsset
from app.design_sync.repository import DesignSyncRepository


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    return db


@pytest.fixture
def repo(mock_db: AsyncMock) -> DesignSyncRepository:
    return DesignSyncRepository(mock_db)


class TestCreateImport:
    @pytest.mark.asyncio
    async def test_creates_with_pending_status(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        await repo.create_import(
            connection_id=1,
            project_id=2,
            selected_node_ids=["1:2", "3:4"],
            created_by_id=10,
        )
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, DesignImport)
        assert added.status == "pending"
        assert added.selected_node_ids == ["1:2", "3:4"]
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


class TestGetImport:
    @pytest.mark.asyncio
    async def test_returns_none_when_missing(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_import(999)
        assert result is None


class TestUpdateImportStatus:
    @pytest.mark.asyncio
    async def test_updates_status_and_fields(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        design_import = DesignImport(
            connection_id=1,
            project_id=2,
            status="pending",
            selected_node_ids=["1:2"],
            created_by_id=10,
        )
        await repo.update_import_status(
            design_import,
            "extracting",
            structure_json={"pages": []},
        )
        assert design_import.status == "extracting"
        assert design_import.structure_json == {"pages": []}
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_updates_error_on_failure(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        design_import = DesignImport(
            connection_id=1,
            project_id=2,
            status="extracting",
            selected_node_ids=["1:2"],
            created_by_id=10,
        )
        await repo.update_import_status(
            design_import,
            "failed",
            error_message="Figma API rate limited",
        )
        assert design_import.status == "failed"
        assert design_import.error_message == "Figma API rate limited"


class TestCancelImport:
    @pytest.mark.asyncio
    async def test_cancels_pending_import(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        design_import = DesignImport(
            connection_id=1,
            project_id=2,
            status="pending",
            selected_node_ids=["1:2"],
            created_by_id=10,
        )
        await repo.cancel_import(design_import)
        assert design_import.status == "cancelled"

    @pytest.mark.asyncio
    async def test_does_not_cancel_completed(
        self, repo: DesignSyncRepository, mock_db: AsyncMock
    ) -> None:
        design_import = DesignImport(
            connection_id=1,
            project_id=2,
            status="completed",
            selected_node_ids=["1:2"],
            created_by_id=10,
        )
        await repo.cancel_import(design_import)
        assert design_import.status == "completed"  # unchanged


class TestCreateImportAsset:
    @pytest.mark.asyncio
    async def test_creates_asset(self, repo: DesignSyncRepository, mock_db: AsyncMock) -> None:
        await repo.create_import_asset(
            import_id=1,
            node_id="1:2",
            node_name="Hero Image",
            file_path="1_2.png",
            width=1200,
            height=600,
            format="png",
            usage="hero",
        )
        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert isinstance(added, DesignImportAsset)
        assert added.node_id == "1:2"
        assert added.usage == "hero"


class TestBulkCreateImportAssets:
    @pytest.mark.asyncio
    async def test_creates_multiple(self, repo: DesignSyncRepository, mock_db: AsyncMock) -> None:
        assets_data: list[dict[str, object]] = [
            {"node_id": "1:2", "node_name": "Hero", "file_path": "1_2.png", "usage": "hero"},
            {"node_id": "3:4", "node_name": "Logo", "file_path": "3_4.png", "usage": "logo"},
        ]
        await repo.bulk_create_import_assets(import_id=1, assets=assets_data)
        mock_db.add_all.assert_called_once()
        models = mock_db.add_all.call_args[0][0]
        assert len(models) == 2
        assert models[0].node_name == "Hero"
        assert models[1].usage == "logo"


class TestListImportAssets:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, repo: DesignSyncRepository, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await repo.list_import_assets(999)
        assert result == []
