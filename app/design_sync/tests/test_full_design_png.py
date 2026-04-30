"""Tests for full-design PNG threading (Phase 50.1, Gap 9)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.protocols import CompletionResponse
from app.design_sync.component_matcher import match_all
from app.design_sync.figma.layout_analyzer import (
    EmailSection,
    EmailSectionType,
    analyze_layout,
)
from app.design_sync.figma.service import FigmaDesignSyncService
from app.design_sync.protocol import DesignFileStructure, ExportedImage
from app.design_sync.tests.conftest import make_file_structure
from app.design_sync.visual_verify import clear_verify_cache, compare_sections
from app.rendering.visual_diff import DiffResult

_FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_GLOBAL_PNG = b"\x89PNG\r\n\x1a\nGLOBAL" + b"\x00" * 100


def _make_exported(node_id: str = "1:1") -> ExportedImage:
    return ExportedImage(
        node_id=node_id,
        url="https://figma-cdn.example/test.png",
        format="png",
        expires_at=datetime.now(tz=UTC),
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    clear_verify_cache()
    yield
    clear_verify_cache()


# ── _export_full_frame_png helper ──────────────────────────────────────────


class TestExportFullFramePng:
    @pytest.mark.asyncio
    async def test_export_full_frame_png_success(self) -> None:
        """Happy path: export_images succeeds and download yields bytes."""
        svc = FigmaDesignSyncService()
        with (
            patch.object(
                svc,
                "export_images",
                new=AsyncMock(return_value=[_make_exported("1:1")]),
            ),
            patch.object(
                svc,
                "download_image_bytes",
                new=AsyncMock(return_value=_FAKE_PNG),
            ),
        ):
            result = await svc._export_full_frame_png("file", "token", "1:1")

        assert result == _FAKE_PNG

    @pytest.mark.asyncio
    async def test_export_full_frame_png_returns_none_on_api_error(self) -> None:
        """export_images raises -> graceful None, no exception bubbles."""
        svc = FigmaDesignSyncService()
        with patch.object(
            svc,
            "export_images",
            new=AsyncMock(side_effect=RuntimeError("Figma 500")),
        ):
            result = await svc._export_full_frame_png("file", "token", "1:1")

        assert result is None

    @pytest.mark.asyncio
    async def test_export_full_frame_png_returns_none_on_download_error(self) -> None:
        """download_image_bytes raises -> graceful None."""
        svc = FigmaDesignSyncService()
        with (
            patch.object(
                svc,
                "export_images",
                new=AsyncMock(return_value=[_make_exported("1:1")]),
            ),
            patch.object(
                svc,
                "download_image_bytes",
                new=AsyncMock(side_effect=TimeoutError("CDN slow")),
            ),
        ):
            result = await svc._export_full_frame_png("file", "token", "1:1")

        assert result is None

    @pytest.mark.asyncio
    async def test_export_full_frame_png_missing_node_returns_none(self) -> None:
        """export_images returns image for a different node id -> None."""
        svc = FigmaDesignSyncService()
        with patch.object(
            svc,
            "export_images",
            new=AsyncMock(return_value=[_make_exported("9:9")]),
        ):
            result = await svc._export_full_frame_png("file", "token", "1:1")

        assert result is None


# ── DesignFileStructure carries the PNG ────────────────────────────────────


class TestDesignFileStructure:
    def test_design_file_structure_carries_png(self) -> None:
        """New design_image field accepts bytes and defaults to None."""
        with_png = DesignFileStructure(file_name="test.fig", pages=[], design_image=_FAKE_PNG)
        assert with_png.design_image == _FAKE_PNG

        without_png = DesignFileStructure(file_name="test.fig", pages=[])
        assert without_png.design_image is None


# ── Pass-through wiring ────────────────────────────────────────────────────


class TestPassThrough:
    def test_analyze_layout_accepts_global_design_image(self) -> None:
        """analyze_layout accepts the new kwarg without altering behaviour."""
        structure = make_file_structure()
        with_image = analyze_layout(structure, global_design_image=_GLOBAL_PNG)
        without_image = analyze_layout(structure)

        assert with_image.file_name == without_image.file_name
        assert len(with_image.sections) == len(without_image.sections)

    def test_match_all_accepts_global_design_image(self) -> None:
        """match_all accepts the new kwarg without altering output."""
        sections: list[EmailSection] = [
            EmailSection(
                section_type=EmailSectionType.HERO,
                node_id="1:1",
                node_name="Hero",
            )
        ]
        with_image = match_all(sections, global_design_image=_GLOBAL_PNG)
        without_image = match_all(sections)

        assert len(with_image) == len(without_image) == 1
        assert with_image[0].component_slug == without_image[0].component_slug


# ── Low-confidence VLM fallback uses the global PNG ────────────────────────


def _mock_settings_for_verify(
    *,
    diff_skip: float = 2.0,
    low_threshold: float = 0.7,
) -> Any:
    """Patch get_settings inside visual_verify with VLM-verify config."""
    mock_ds = type(
        "DS",
        (),
        {
            "vlm_verify_enabled": True,
            "vlm_verify_model": "",
            "vlm_verify_timeout": 5.0,
            "vlm_verify_diff_skip_threshold": diff_skip,
            "vlm_verify_max_sections": 20,
            "vlm_low_confidence_threshold": low_threshold,
        },
    )()
    mock_s = type("S", (), {"design_sync": mock_ds})()
    return patch("app.design_sync.visual_verify.get_settings", return_value=mock_s)


def _mock_odiff(diff_pct: float) -> Any:
    result = DiffResult(
        identical=diff_pct == 0.0,
        diff_percentage=diff_pct,
        diff_image=None,
        pixel_count=int(diff_pct * 100),
        changed_regions=[],
    )
    return patch(
        "app.rendering.visual_diff.run_odiff",
        new_callable=AsyncMock,
        return_value=result,
    )


def _make_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.complete.return_value = CompletionResponse(
        content="[]",
        model="test",
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    )
    return provider


def _make_section(node_id: str = "n1") -> EmailSection:
    return EmailSection(
        section_type=EmailSectionType.HERO,
        node_id=node_id,
        node_name="Hero",
    )


class TestVisualVerifyLowConfidence:
    @pytest.mark.asyncio
    async def test_visual_verify_low_confidence_uses_global_png(self) -> None:
        """fidelity < threshold AND global_design_image set -> 3 ImageBlocks in VLM call."""
        from app.ai.multimodal import ImageBlock

        provider = _make_provider()

        # diff 50% -> fidelity 0.5, well below 0.7 threshold -> global PNG must be passed.
        with (
            _mock_settings_for_verify(diff_skip=2.0, low_threshold=0.7),
            _mock_odiff(diff_pct=50.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
                global_design_image=_GLOBAL_PNG,
            )

        provider.complete.assert_awaited_once()
        # Inspect the messages passed to the VLM
        call = provider.complete.await_args
        messages = call.kwargs["messages"]
        content = messages[0].content
        image_blocks = [b for b in content if isinstance(b, ImageBlock)]
        assert len(image_blocks) == 3, (
            "Low-fidelity VLM call must receive figma + rendered + global PNG"
        )
        assert image_blocks[2].data == _GLOBAL_PNG

    @pytest.mark.asyncio
    async def test_visual_verify_high_fidelity_skips_global_png(self) -> None:
        """fidelity above threshold -> only 2 ImageBlocks (no global)."""
        from app.ai.multimodal import ImageBlock

        provider = _make_provider()

        # diff 10% -> fidelity 0.9 > 0.7 threshold -> no global PNG.
        with (
            _mock_settings_for_verify(diff_skip=2.0, low_threshold=0.7),
            _mock_odiff(diff_pct=10.0),
            patch("app.ai.registry.get_registry") as mock_reg,
            patch(
                "app.ai.routing.resolve_model_by_capabilities",
                return_value="test-model",
            ),
        ):
            mock_reg.return_value.get_llm.return_value = provider
            await compare_sections(
                {"n1": _FAKE_PNG},
                {"n1": _FAKE_PNG},
                "<html></html>",
                [_make_section("n1")],
                global_design_image=_GLOBAL_PNG,
            )

        provider.complete.assert_awaited_once()
        call = provider.complete.await_args
        messages = call.kwargs["messages"]
        content = messages[0].content
        image_blocks = [b for b in content if isinstance(b, ImageBlock)]
        assert len(image_blocks) == 2


# ── Disabled flag short-circuits the export ────────────────────────────────


class TestDisabledFlag:
    @pytest.mark.asyncio
    async def test_full_design_png_disabled_flag(self) -> None:
        """full_design_png_enabled=False -> _export_full_frame_png never called."""
        svc = FigmaDesignSyncService()

        # Build minimal Figma file payload that sync_tokens_and_structure can parse.
        file_data: dict[str, Any] = {
            "name": "Test",
            "document": {"id": "0:0", "type": "DOCUMENT", "children": []},
            "styles": {},
        }

        file_resp = MagicMock()
        file_resp.status_code = 200
        file_resp.json.return_value = file_data

        styles_resp = MagicMock()
        styles_resp.status_code = 200
        styles_resp.json.return_value = {}

        client = AsyncMock()
        client.get = AsyncMock(side_effect=[file_resp, styles_resp])
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        # Settings: flag off, scoping off so the empty document is fine.
        mock_ds = MagicMock()
        mock_ds.full_design_png_enabled = False
        mock_ds.token_scoping_enabled = False
        mock_ds.figma_variables_enabled = False
        mock_ds.opacity_composite_bg = "#FFFFFF"
        mock_settings = MagicMock()
        mock_settings.design_sync = mock_ds

        with (
            patch("app.design_sync.figma.service.httpx.AsyncClient", return_value=client),
            patch(
                "app.design_sync.figma.service.get_settings",
                return_value=mock_settings,
            ),
            patch.object(
                svc,
                "_export_full_frame_png",
                new=AsyncMock(return_value=b"should-not-be-returned"),
            ) as mock_export,
        ):
            _, structure = await svc.sync_tokens_and_structure(
                "file", "token", target_node_id="1:1"
            )

        mock_export.assert_not_awaited()
        assert structure.design_image is None
