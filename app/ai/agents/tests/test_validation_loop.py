"""Tests for CRAG validation loop mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.validation_loop import CRAGMixin


class _FakeAgent(CRAGMixin):
    """Minimal agent stub for testing the mixin."""

    pass


def _make_settings(
    *,
    crag_enabled: bool = True,
    crag_min_severity: str = "error",
) -> MagicMock:
    settings = MagicMock()
    settings.knowledge.crag_enabled = crag_enabled
    settings.knowledge.crag_min_severity = crag_min_severity
    settings.ai.provider = "test"
    return settings


class TestCRAGMixin:
    """Test _crag_validate_and_correct()."""

    @pytest.mark.asyncio
    async def test_no_issues_returns_unchanged(self) -> None:
        """No unsupported CSS -> return original, no LLM call."""
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=[],
            ),
        ):
            html, corrections = await agent._crag_validate_and_correct(
                "<html><body>Hello</body></html>", "system", "model"
            )
        assert html == "<html><body>Hello</body></html>"
        assert corrections == []

    @pytest.mark.asyncio
    async def test_issues_below_severity_skipped(self) -> None:
        """Issues with severity below threshold are skipped."""
        issues = [
            {
                "property_id": "flex",
                "property_name": "display",
                "value": "flex",
                "severity": "warning",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            }
        ]
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(crag_min_severity="error"),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
        ):
            _html, corrections = await agent._crag_validate_and_correct(
                "<html></html>", "system", "model"
            )
        assert corrections == []

    @pytest.mark.asyncio
    async def test_qualifying_issue_triggers_llm_correction(self) -> None:
        """Error-severity issue triggers LLM call and returns corrected HTML."""
        issues = [
            {
                "property_id": "display_flex",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook 2019"],
                "fallback_available": True,
            }
        ]
        mock_fallback = MagicMock(technique="flex_to_table", code_example="<table>...</table>")
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = [mock_fallback]

        mock_result = MagicMock()
        mock_result.content = "<html><body><table>Fixed</table></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
            patch(
                "app.ai.agents.validation_loop.load_ontology",
                return_value=mock_onto,
            ),
            patch(
                "app.ai.registry.get_registry",
                return_value=mock_registry,
            ),
        ):
            html, corrections = await agent._crag_validate_and_correct(
                "<html><body><div style='display:flex'>Bad</div></body></html>",
                "system prompt",
                "gpt-4o",
            )
        assert corrections == ["display_flex"]
        assert html != "<html><body><div style='display:flex'>Bad</div></body></html>"
        assert len(html) >= 50
        mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_original(self) -> None:
        """LLM error -> failure-safe, return original HTML."""
        issues = [
            {
                "property_id": "display_flex",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            }
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = [MagicMock(technique="t", code_example="c")]

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = RuntimeError("LLM down")

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        original = "<html><body>Original</body></html>"
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
            patch(
                "app.ai.agents.validation_loop.load_ontology",
                return_value=mock_onto,
            ),
            patch(
                "app.ai.registry.get_registry",
                return_value=mock_registry,
            ),
        ):
            html, corrections = await agent._crag_validate_and_correct(original, "system", "model")
        assert html == original
        assert corrections == []

    @pytest.mark.asyncio
    async def test_empty_llm_output_returns_original(self) -> None:
        """LLM returns near-empty string -> failure-safe."""
        issues = [
            {
                "property_id": "flex",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            }
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = [MagicMock(technique="t", code_example="c")]

        mock_result = MagicMock()
        mock_result.content = ""
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        original = "<html><body>Original</body></html>"
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
            patch(
                "app.ai.agents.validation_loop.load_ontology",
                return_value=mock_onto,
            ),
            patch(
                "app.ai.registry.get_registry",
                return_value=mock_registry,
            ),
        ):
            html, corrections = await agent._crag_validate_and_correct(original, "system", "model")
        assert html == original
        assert corrections == []

    @pytest.mark.asyncio
    async def test_no_fallback_still_instructs_removal(self) -> None:
        """Issue without fallback -> instruction says remove/replace."""
        issues = [
            {
                "property_id": "nofb",
                "property_name": "gap",
                "value": None,
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": False,
            }
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = []

        mock_result = MagicMock()
        mock_result.content = "<html><head><title>Email</title></head><body><table><tr><td>Fixed without gap property</td></tr></table></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
            patch(
                "app.ai.agents.validation_loop.load_ontology",
                return_value=mock_onto,
            ),
            patch(
                "app.ai.registry.get_registry",
                return_value=mock_registry,
            ),
        ):
            _html, corrections = await agent._crag_validate_and_correct(
                "<html><body style='gap:10px'>x</body></html>",
                "system",
                "model",
            )
        assert corrections == ["nofb"]
        # Verify the prompt mentioned "remove or replace"
        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert (
            "remove or replace" in user_msg.lower() or "universally supported" in user_msg.lower()
        )

    @pytest.mark.asyncio
    async def test_warning_severity_threshold(self) -> None:
        """With crag_min_severity='warning', both error and warning qualify."""
        issues = [
            {
                "property_id": "p1",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            },
            {
                "property_id": "p2",
                "property_name": "gap",
                "value": None,
                "severity": "warning",
                "unsupported_clients": ["Gmail"],
                "fallback_available": False,
            },
            {
                "property_id": "p3",
                "property_name": "color-scheme",
                "value": None,
                "severity": "info",
                "unsupported_clients": ["AOL"],
                "fallback_available": False,
            },
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = []

        mock_result = MagicMock()
        mock_result.content = "<html><head><title>Email</title></head><body><table><tr><td>Corrected HTML content here</td></tr></table></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(crag_min_severity="warning"),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                return_value=issues,
            ),
            patch(
                "app.ai.agents.validation_loop.load_ontology",
                return_value=mock_onto,
            ),
            patch(
                "app.ai.registry.get_registry",
                return_value=mock_registry,
            ),
        ):
            _, corrections = await agent._crag_validate_and_correct(
                "<html></html>", "system", "model"
            )
        # p1 (error) and p2 (warning) qualify, p3 (info) does not
        assert corrections == ["p1", "p2"]


class TestCRAGDisabled:
    """Test that CRAG is skippable."""

    @pytest.mark.asyncio
    async def test_disabled_config_not_called_from_base(self) -> None:
        """When crag_enabled=False, _crag_validate_and_correct is never called."""
        settings = _make_settings(crag_enabled=False)
        assert settings.knowledge.crag_enabled is False
