# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Unit tests for ODiff visual diff service, baseline repository, service layer, and routes."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rendering.exceptions import RenderingProviderError, VisualDiffError
from app.rendering.schemas import VALID_ENTITY_TYPES
from app.rendering.visual_diff import DiffResult, compare_images, run_odiff

# Small 1x1 white PNG for testing (base64)
TINY_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
    "nGP4z8BQDwAEgAF/pooBPQAAAABJRU5ErkJggg=="
)
TINY_PNG_BYTES = base64.b64decode(TINY_PNG)


# ── ODiff subprocess wrapper (mocked) ──


class TestRunOdiff:
    """Tests for the ODiff subprocess wrapper."""

    @pytest.mark.asyncio()
    async def test_compare_identical_images(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            result = await run_odiff(baseline, current, output)

        assert result.identical is True
        assert result.diff_percentage == 0.0
        assert result.diff_image is None
        assert result.pixel_count == 0

    @pytest.mark.asyncio()
    async def test_compare_different_images(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)
        output.write_bytes(b"fake-diff-png")

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (
            b"Files are different. 1234 changed pixels (3.45% of all)",
            b"",
        )
        mock_proc.returncode = 1

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            result = await run_odiff(baseline, current, output)

        assert result.identical is False
        assert result.diff_percentage == 3.45
        assert result.pixel_count == 1234
        assert result.diff_image == b"fake-diff-png"

    @pytest.mark.asyncio()
    async def test_compare_dimension_mismatch(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"Images have different dimensions")
        mock_proc.returncode = 2

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            with pytest.raises(VisualDiffError, match="ODiff comparison error"):
                await run_odiff(baseline, current, output)

    @pytest.mark.asyncio()
    async def test_compare_timeout(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = TimeoutError()

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            with patch("app.rendering.visual_diff.asyncio.wait_for", side_effect=TimeoutError()):
                with pytest.raises(VisualDiffError, match="timed out"):
                    await run_odiff(baseline, current, output)

    @pytest.mark.asyncio()
    async def test_compare_binary_not_found(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("npx not found"),
        ):
            with pytest.raises(VisualDiffError, match="not found"):
                await run_odiff(baseline, current, output)

    @pytest.mark.asyncio()
    async def test_diff_percentage_parsing_various_formats(self, tmp_path: Path) -> None:
        """Various stdout formats parse correctly."""
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"12.5% difference", b"")
        mock_proc.returncode = 1

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            result = await run_odiff(baseline, current, output)

        assert result.diff_percentage == 12.5

    @pytest.mark.asyncio()
    async def test_pixel_count_parsing(self, tmp_path: Path) -> None:
        baseline = tmp_path / "a.png"
        current = tmp_path / "b.png"
        output = tmp_path / "diff.png"
        baseline.write_bytes(TINY_PNG_BYTES)
        current.write_bytes(TINY_PNG_BYTES)

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"99 changed pixels (0.5% of all)", b"")
        mock_proc.returncode = 1

        with patch(
            "app.rendering.visual_diff.asyncio.create_subprocess_exec", return_value=mock_proc
        ):
            result = await run_odiff(baseline, current, output)

        assert result.pixel_count == 99
        assert result.diff_percentage == 0.5


# ── compare_images high-level ──


class TestCompareImages:
    """Tests for the high-level compare_images entry point."""

    @pytest.mark.asyncio()
    async def test_compare_images_uses_settings_threshold(self) -> None:
        mock_result = DiffResult(
            identical=True, diff_percentage=0.0, diff_image=None, pixel_count=0, changed_regions=[]
        )
        with patch("app.rendering.visual_diff.run_odiff", return_value=mock_result) as mock_run:
            result = await compare_images(TINY_PNG_BYTES, TINY_PNG_BYTES)

        assert result.identical is True
        # Verify run_odiff was called (threshold from settings default 0.01)
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_compare_images_with_custom_threshold(self) -> None:
        mock_result = DiffResult(
            identical=False,
            diff_percentage=2.0,
            diff_image=None,
            pixel_count=100,
            changed_regions=[],
        )
        with patch("app.rendering.visual_diff.run_odiff", return_value=mock_result) as mock_run:
            result = await compare_images(TINY_PNG_BYTES, TINY_PNG_BYTES, threshold=0.05)

        assert result.identical is False
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["threshold"] == 0.05


# ── Baseline repository (mocked DB) ──


class TestScreenshotBaselineRepository:
    """Tests for the ScreenshotBaselineRepository with mocked DB."""

    @pytest.fixture()
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture()
    def repo(self, mock_db: AsyncMock) -> Any:
        from app.rendering.repository import ScreenshotBaselineRepository

        return ScreenshotBaselineRepository(mock_db)

    @pytest.mark.asyncio()
    async def test_get_by_entity_returns_match(self, repo: Any, mock_db: AsyncMock) -> None:
        mock_baseline = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_baseline
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_entity("component_version", 1, "gmail_web")
        assert result is mock_baseline

    @pytest.mark.asyncio()
    async def test_get_by_entity_returns_none(self, repo: Any, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.get_by_entity("component_version", 999, "nonexistent")
        assert result is None

    @pytest.mark.asyncio()
    async def test_list_by_entity(self, repo: Any, mock_db: AsyncMock) -> None:
        mock_baselines = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_baselines
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repo.list_by_entity("golden_template", 1)
        assert len(result) == 2

    @pytest.mark.asyncio()
    async def test_upsert_creates_new_baseline(self, repo: Any, mock_db: AsyncMock) -> None:
        # get_by_entity returns None → creates new
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await repo.upsert(
            entity_type="component_version",
            entity_id=1,
            client_name="gmail_web",
            image_data=TINY_PNG_BYTES,
            image_hash="abc123",
            created_by_id=1,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio()
    async def test_upsert_updates_existing_baseline(self, repo: Any, mock_db: AsyncMock) -> None:
        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        result = await repo.upsert(
            entity_type="component_version",
            entity_id=1,
            client_name="gmail_web",
            image_data=b"new-data",
            image_hash="new-hash",
            created_by_id=1,
        )

        assert existing.image_data == b"new-data"
        assert existing.image_hash == "new-hash"
        mock_db.commit.assert_awaited()
        assert result is existing

    @pytest.mark.asyncio()
    async def test_delete_by_entity(self, repo: Any, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute.return_value = mock_result

        count = await repo.delete_by_entity("component_version", 1)
        assert count == 3
        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited()


# ── Service layer ──


class TestRenderingServiceVisualDiff:
    """Tests for visual diff methods on RenderingService."""

    @pytest.fixture()
    def service(self) -> Any:
        from app.rendering.service import RenderingService

        return RenderingService(db=AsyncMock())

    @pytest.mark.asyncio()
    async def test_visual_diff_disabled_raises(self, service: Any) -> None:
        from app.rendering.schemas import VisualDiffRequest

        data = VisualDiffRequest(
            baseline_image=TINY_PNG,
            current_image=TINY_PNG,
            threshold=None,
        )
        with patch("app.rendering.service.settings") as mock_settings:
            mock_settings.rendering.visual_diff_enabled = False
            with pytest.raises(RenderingProviderError, match="disabled"):
                await service.visual_diff(data)

    @pytest.mark.asyncio()
    async def test_visual_diff_returns_response(self, service: Any) -> None:
        from app.rendering.schemas import VisualDiffRequest

        data = VisualDiffRequest(
            baseline_image=TINY_PNG,
            current_image=TINY_PNG,
            threshold=None,
        )
        mock_result = DiffResult(
            identical=True,
            diff_percentage=0.0,
            diff_image=None,
            pixel_count=0,
            changed_regions=[],
        )
        with (
            patch("app.rendering.service.settings") as mock_settings,
            patch("app.rendering.service.compare_images", return_value=mock_result),
        ):
            mock_settings.rendering.visual_diff_enabled = True
            mock_settings.rendering.visual_diff_threshold = 0.01
            result = await service.visual_diff(data)

        assert result.identical is True
        assert result.diff_percentage == 0.0
        assert result.threshold_used == 0.01

    @pytest.mark.asyncio()
    async def test_visual_diff_with_custom_threshold(self, service: Any) -> None:
        from app.rendering.schemas import VisualDiffRequest

        data = VisualDiffRequest(
            baseline_image=TINY_PNG,
            current_image=TINY_PNG,
            threshold=0.05,
        )
        mock_result = DiffResult(
            identical=False,
            diff_percentage=3.0,
            diff_image=b"diff-png",
            pixel_count=50,
            changed_regions=[],
        )
        with (
            patch("app.rendering.service.settings") as mock_settings,
            patch("app.rendering.service.compare_images", return_value=mock_result),
        ):
            mock_settings.rendering.visual_diff_enabled = True
            result = await service.visual_diff(data)

        assert result.threshold_used == 0.05
        assert result.diff_image is not None

    @pytest.mark.asyncio()
    async def test_list_baselines_invalid_entity_type(self, service: Any) -> None:
        with pytest.raises(RenderingProviderError, match="Invalid entity_type"):
            await service.list_baselines("invalid_type", 1)

    @pytest.mark.asyncio()
    async def test_list_baselines_returns_list(self, service: Any) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        mock_baseline = MagicMock()
        mock_baseline.id = 1
        mock_baseline.entity_type = "component_version"
        mock_baseline.entity_id = 42
        mock_baseline.client_name = "gmail_web"
        mock_baseline.image_hash = "abc"
        mock_baseline.created_at = now
        mock_baseline.updated_at = now

        service.baseline_repo.list_by_entity = AsyncMock(return_value=[mock_baseline])

        result = await service.list_baselines("component_version", 42)
        assert result.entity_type == "component_version"
        assert result.entity_id == 42
        assert len(result.baselines) == 1
        assert result.baselines[0].client_name == "gmail_web"

    @pytest.mark.asyncio()
    async def test_update_baseline_creates(self, service: Any) -> None:
        from app.rendering.schemas import BaselineUpdateRequest

        now = datetime(2026, 1, 1, tzinfo=UTC)
        mock_baseline = MagicMock()
        mock_baseline.id = 1
        mock_baseline.entity_type = "golden_template"
        mock_baseline.entity_id = 10
        mock_baseline.client_name = "outlook_2019"
        mock_baseline.image_hash = hashlib.sha256(TINY_PNG_BYTES).hexdigest()
        mock_baseline.created_at = now
        mock_baseline.updated_at = now

        service.baseline_repo.upsert = AsyncMock(return_value=mock_baseline)

        data = BaselineUpdateRequest(client_name="outlook_2019", image_base64=TINY_PNG)
        result = await service.update_baseline("golden_template", 10, data, user_id=1)

        assert result.client_name == "outlook_2019"
        assert result.image_hash == hashlib.sha256(TINY_PNG_BYTES).hexdigest()

    @pytest.mark.asyncio()
    async def test_update_baseline_computes_sha256(self, service: Any) -> None:
        from app.rendering.schemas import BaselineUpdateRequest

        now = datetime(2026, 1, 1, tzinfo=UTC)
        mock_baseline = MagicMock()
        mock_baseline.id = 1
        mock_baseline.entity_type = "component_version"
        mock_baseline.entity_id = 5
        mock_baseline.client_name = "apple_mail"
        mock_baseline.image_hash = hashlib.sha256(TINY_PNG_BYTES).hexdigest()
        mock_baseline.created_at = now
        mock_baseline.updated_at = now

        service.baseline_repo.upsert = AsyncMock(return_value=mock_baseline)

        data = BaselineUpdateRequest(client_name="apple_mail", image_base64=TINY_PNG)
        await service.update_baseline("component_version", 5, data, user_id=1)

        call_kwargs = service.baseline_repo.upsert.call_args.kwargs
        assert call_kwargs["image_hash"] == hashlib.sha256(TINY_PNG_BYTES).hexdigest()
        assert call_kwargs["image_data"] == TINY_PNG_BYTES


# ── Route layer ──


class TestVisualDiffRoutes:
    """Tests for visual diff and baseline endpoints."""

    @pytest.fixture()
    def app(self) -> FastAPI:
        from app.rendering.routes import router

        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture()
    def client(self, app: FastAPI) -> TestClient:
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def _disable_rate_limit(self) -> Any:
        from app.core.rate_limit import limiter

        limiter.enabled = False
        yield
        limiter.enabled = True

    def test_visual_diff_endpoint_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/rendering/visual-diff",
            json={
                "baseline_image": TINY_PNG,
                "current_image": TINY_PNG,
            },
        )
        assert resp.status_code in (401, 403)

    def test_list_baselines_endpoint_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/rendering/baselines/component_version/1")
        assert resp.status_code in (401, 403)

    def test_update_baseline_endpoint_requires_auth(self, client: TestClient) -> None:
        resp = client.put(
            "/api/v1/rendering/baselines/component_version/1",
            json={"client_name": "gmail_web", "image_base64": TINY_PNG},
        )
        assert resp.status_code in (401, 403)

    def test_visual_diff_endpoint_success(self, app: FastAPI) -> None:
        from app.auth.dependencies import get_current_user
        from app.rendering.routes import get_service
        from app.rendering.schemas import VisualDiffResponse

        mock_response = VisualDiffResponse(
            identical=True,
            diff_percentage=0.0,
            diff_image=None,
            pixel_count=0,
            changed_regions=[],
            threshold_used=0.01,
        )

        mock_service = AsyncMock()
        mock_service.visual_diff.return_value = mock_response
        mock_user = MagicMock()
        mock_user.role = "developer"

        app.dependency_overrides[get_service] = lambda: mock_service
        app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            test_client = TestClient(app)
            resp = test_client.post(
                "/api/v1/rendering/visual-diff",
                json={
                    "baseline_image": TINY_PNG,
                    "current_image": TINY_PNG,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["identical"] is True
        finally:
            app.dependency_overrides.clear()

    def test_list_baselines_endpoint_success(self, app: FastAPI) -> None:
        from app.auth.dependencies import get_current_user
        from app.rendering.routes import get_service
        from app.rendering.schemas import BaselineListResponse

        mock_response = BaselineListResponse(
            entity_type="component_version",
            entity_id=1,
            baselines=[],
        )

        mock_service = AsyncMock()
        mock_service.list_baselines.return_value = mock_response
        mock_user = MagicMock()

        app.dependency_overrides[get_service] = lambda: mock_service
        app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            test_client = TestClient(app)
            resp = test_client.get("/api/v1/rendering/baselines/component_version/1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["entity_type"] == "component_version"
            assert data["baselines"] == []
        finally:
            app.dependency_overrides.clear()

    def test_update_baseline_endpoint_success(self, app: FastAPI) -> None:
        from app.auth.dependencies import get_current_user
        from app.rendering.routes import get_service
        from app.rendering.schemas import BaselineResponse

        now = datetime(2026, 1, 1, tzinfo=UTC)
        mock_response = BaselineResponse(
            id=1,
            entity_type="component_version",
            entity_id=1,
            client_name="gmail_web",
            image_hash="abc",
            created_at=now,
            updated_at=now,
        )

        mock_service = AsyncMock()
        mock_service.update_baseline.return_value = mock_response
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "developer"

        app.dependency_overrides[get_service] = lambda: mock_service
        app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            test_client = TestClient(app)
            resp = test_client.put(
                "/api/v1/rendering/baselines/component_version/1",
                json={"client_name": "gmail_web", "image_base64": TINY_PNG},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["client_name"] == "gmail_web"
        finally:
            app.dependency_overrides.clear()


# ── Schema validation ──


class TestSchemaValidation:
    """Tests for Pydantic schema validation."""

    def test_valid_entity_types_set(self) -> None:
        assert "component_version" in VALID_ENTITY_TYPES
        assert "golden_template" in VALID_ENTITY_TYPES
        assert len(VALID_ENTITY_TYPES) == 2

    def test_visual_diff_request_threshold_range(self) -> None:
        from app.rendering.schemas import VisualDiffRequest

        # Valid
        req = VisualDiffRequest(baseline_image="a", current_image="b", threshold=0.5)
        assert req.threshold == 0.5

        # Out of range
        with pytest.raises(Exception):  # noqa: B017
            VisualDiffRequest(baseline_image="a", current_image="b", threshold=1.5)

        with pytest.raises(Exception):  # noqa: B017
            VisualDiffRequest(baseline_image="a", current_image="b", threshold=-0.1)

    def test_baseline_update_request_validates(self) -> None:
        from app.rendering.schemas import BaselineUpdateRequest

        req = BaselineUpdateRequest(client_name="gmail_web", image_base64=TINY_PNG)
        assert req.client_name == "gmail_web"

        with pytest.raises(Exception):  # noqa: B017
            BaselineUpdateRequest(client_name="gmail_web", image_base64="")
