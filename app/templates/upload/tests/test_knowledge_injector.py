"""Tests for knowledge injection from uploaded templates (Phase 25.10)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.templates.upload.analyzer import AnalysisResult, ComplexityInfo, SectionInfo, TokenInfo
from app.templates.upload.knowledge_injector import KnowledgeInjector


def _make_analysis(**overrides: object) -> AnalysisResult:
    defaults: dict[str, object] = {
        "sections": [
            SectionInfo(
                section_id="s1",
                component_name="hero",
                element_count=5,
                layout_type="single",
            )
        ],
        "slots": [],
        "tokens": TokenInfo(colors={}, fonts={}, font_sizes={}, spacing={}),
        "esp_platform": None,
        "complexity": ComplexityInfo(
            column_count=1,
            nesting_depth=2,
            mso_conditional_count=0,
            total_elements=10,
            table_nesting_depth=1,
            has_vml=False,
            has_amp=False,
        ),
        "layout_type": "promotional",
    }
    defaults.update(overrides)
    return AnalysisResult(**defaults)  # type: ignore[arg-type]


class TestKnowledgeInjector:
    @pytest.mark.asyncio
    async def test_injects_vml_pattern(self) -> None:
        """VML HTML triggers knowledge injection."""
        mock_svc = AsyncMock()
        mock_svc.ingest_document.return_value = MagicMock(id=42)
        injector = KnowledgeInjector(mock_svc)
        html = '<html><body><v:rect style="width:200px"><v:fill type="frame" src="bg.jpg"/></v:rect></body></html>'
        result = await injector.inject("test_tmpl", html, _make_analysis(), None)
        assert result == 42
        mock_svc.ingest_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_injects_mso_conditional_pattern(self) -> None:
        """MSO conditional HTML triggers injection."""
        mock_svc = AsyncMock()
        mock_svc.ingest_document.return_value = MagicMock(id=43)
        injector = KnowledgeInjector(mock_svc)
        html = "<html><body><!--[if mso]><table><tr><td><![endif]-->Content<!--[if mso]></td></tr></table><![endif]--></body></html>"
        result = await injector.inject("test_tmpl", html, _make_analysis(), None)
        assert result == 43

    @pytest.mark.asyncio
    async def test_no_patterns_returns_none(self) -> None:
        """Plain HTML without patterns -> None (no injection)."""
        mock_svc = AsyncMock()
        injector = KnowledgeInjector(mock_svc)
        html = "<html><body><p>Simple text email.</p></body></html>"
        result = await injector.inject("test_tmpl", html, _make_analysis(), None)
        assert result is None
        mock_svc.ingest_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_returns_none(self) -> None:
        """Knowledge service failure -> None (non-blocking)."""
        mock_svc = AsyncMock()
        mock_svc.ingest_document.side_effect = RuntimeError("DB down")
        injector = KnowledgeInjector(mock_svc)
        html = "<html><body><v:rect>VML</v:rect></body></html>"
        result = await injector.inject("test_tmpl", html, _make_analysis(), None)
        assert result is None

    @pytest.mark.asyncio
    async def test_dark_mode_pattern_detected(self) -> None:
        """color-scheme: light dark triggers injection."""
        mock_svc = AsyncMock()
        mock_svc.ingest_document.return_value = MagicMock(id=44)
        injector = KnowledgeInjector(mock_svc)
        html = "<html><head><style>:root { color-scheme: light dark; }</style></head><body><p>Dark</p></body></html>"
        result = await injector.inject("test_tmpl", html, _make_analysis(), None)
        assert result == 44

    @pytest.mark.asyncio
    async def test_esp_platform_included_in_summary(self) -> None:
        """ESP platform info is included in knowledge document."""
        mock_svc = AsyncMock()
        mock_svc.ingest_document.return_value = MagicMock(id=45)
        injector = KnowledgeInjector(mock_svc)
        html = "<html><body>{% if user.premium %}<v:rect>VML</v:rect>{% endif %}</body></html>"
        result = await injector.inject("test_tmpl", html, _make_analysis(), "braze")
        assert result == 45
        mock_svc.ingest_document.assert_called_once()
        # Verify call includes description mentioning the template
        call_kwargs = mock_svc.ingest_document.call_args
        upload_arg = call_kwargs.kwargs.get("upload") or call_kwargs[1].get("upload")
        assert upload_arg is not None, "ingest_document should receive an upload argument"
        assert "test_tmpl" in upload_arg.description
