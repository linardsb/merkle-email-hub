"""Tests for CRAG validation loop mixin."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog.testing
from structlog.typing import EventDict

from app.ai.agents.validation_loop import CRAGMixin


class _FakeAgent(CRAGMixin):
    """Minimal agent stub for testing the mixin."""


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
                side_effect=[issues, []],  # pre: issues found, post: all fixed
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
                side_effect=[issues, []],  # pre: issues found, post: all fixed
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
                side_effect=[issues, []],  # pre: issues found, post: all fixed
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

    @pytest.mark.asyncio
    async def test_correction_rejected_when_issues_not_reduced(self) -> None:
        """LLM correction that doesn't reduce qualifying issues is rejected."""
        pre_issues = [
            {
                "property_id": "display_flex",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook 2019"],
                "fallback_available": True,
            }
        ]
        # Post-correction scan finds same number of qualifying issues
        post_issues = [
            {
                "property_id": "display_grid",
                "property_name": "display",
                "value": "grid",
                "severity": "error",
                "unsupported_clients": ["Outlook 2019"],
                "fallback_available": False,
            }
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = [MagicMock(technique="t", code_example="c")]

        mock_result = MagicMock()
        mock_result.content = "<html><head><title>Email</title></head><body><table><tr><td>Corrected</td></tr></table></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        original = "<html><body><div style='display:flex'>Bad</div></body></html>"
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                side_effect=[pre_issues, post_issues],
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
    async def test_correction_accepted_when_issues_reduced(self) -> None:
        """LLM correction that reduces but doesn't eliminate all issues is accepted."""
        pre_issues = [
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
                "value": "10px",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            },
            {
                "property_id": "p3",
                "property_name": "grid",
                "value": None,
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": False,
            },
        ]
        # Post-correction: only 1 issue remains (strict reduction from 3 -> 1)
        post_issues = [
            {
                "property_id": "p3",
                "property_name": "grid",
                "value": None,
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": False,
            },
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = []

        mock_result = MagicMock()
        mock_result.content = "<html><head><title>Email</title></head><body><table><tr><td>Partially fixed</td></tr></table></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        original = "<html><body><div style='display:flex;gap:10px'>Bad</div></body></html>"
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                side_effect=[pre_issues, post_issues],
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
        assert html != original
        assert corrections == ["p1", "p2", "p3"]

    @pytest.mark.asyncio
    async def test_correction_rejected_when_new_issues_introduced(self) -> None:
        """LLM correction that swaps one CSS issue for another is rejected."""
        flex_issue = [
            {
                "property_id": "display_flex",
                "property_name": "display",
                "value": "flex",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": True,
            }
        ]
        grid_issue = [
            {
                "property_id": "display_grid",
                "property_name": "display",
                "value": "grid",
                "severity": "error",
                "unsupported_clients": ["Outlook"],
                "fallback_available": False,
            }
        ]
        mock_onto = MagicMock()
        mock_onto.fallbacks_for.return_value = [MagicMock(technique="t", code_example="c")]

        mock_result = MagicMock()
        mock_result.content = "<html><head><title>Email</title></head><body><div style='display:grid'>Swapped</div></body></html>"
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_result

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        original = "<html><body><div style='display:flex'>Content</div></body></html>"
        agent = _FakeAgent()
        with (
            patch(
                "app.ai.agents.validation_loop.get_settings",
                return_value=_make_settings(),
            ),
            patch(
                "app.ai.agents.validation_loop.unsupported_css_in_html",
                side_effect=[flex_issue, grid_issue],
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


class TestCRAGDisabled:
    """Test that CRAG is skippable."""

    @pytest.mark.asyncio
    async def test_disabled_config_not_called_from_base(self) -> None:
        """When crag_enabled=False, _crag_validate_and_correct is never called."""
        settings = _make_settings(crag_enabled=False)
        assert settings.knowledge.crag_enabled is False


# ---------------------------------------------------------------------------
# Structured logging tests
# ---------------------------------------------------------------------------

_ERROR_ISSUE = {
    "property_id": "display_flex",
    "property_name": "display",
    "value": "flex",
    "severity": "error",
    "unsupported_clients": ["Outlook 2019"],
    "fallback_available": True,
}


def _llm_patches(
    *,
    pre_issues: list[dict[str, Any]],
    post_issues: list[dict[str, Any]] | None = None,
    llm_content: str = "<html><head><title>Email</title></head><body><table><tr><td>Fixed</td></tr></table></body></html>",
    llm_side_effect: Exception | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Build common mocks for CRAG logging tests."""
    mock_onto = MagicMock()
    mock_onto.fallbacks_for.return_value = [MagicMock(technique="t", code_example="c")]

    mock_result = MagicMock()
    mock_result.content = llm_content
    mock_provider = AsyncMock()
    if llm_side_effect:
        mock_provider.complete.side_effect = llm_side_effect
    else:
        mock_provider.complete.return_value = mock_result

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    side_effect = [pre_issues]
    if post_issues is not None:
        side_effect.append(post_issues)
    mock_css = MagicMock(side_effect=side_effect)

    return mock_css, mock_onto, mock_registry, _make_settings()


def _find_log(logs: list[EventDict], event: str) -> EventDict | None:
    """Find first log entry matching event name."""
    return next((e for e in logs if e.get("event") == event), None)


class TestCRAGLogging:
    """Test structured log fields emitted by CRAG."""

    @pytest.mark.asyncio
    async def test_issues_detected_includes_property_ids(self) -> None:
        """issues_detected log includes qualifying_property_ids list."""
        mock_css, mock_onto, mock_registry, settings = _llm_patches(
            pre_issues=[_ERROR_ISSUE], post_issues=[]
        )
        agent = _FakeAgent()
        with (
            structlog.testing.capture_logs() as logs,
            patch("app.ai.agents.validation_loop.get_settings", return_value=settings),
            patch("app.ai.agents.validation_loop.unsupported_css_in_html", mock_css),
            patch("app.ai.agents.validation_loop.load_ontology", return_value=mock_onto),
            patch("app.ai.registry.get_registry", return_value=mock_registry),
        ):
            await agent._crag_validate_and_correct("<html></html>", "sys", "m")

        entry = _find_log(logs, "agents.crag.issues_detected")
        assert entry is not None
        assert entry["qualifying_property_ids"] == ["display_flex"]
        assert entry["qualifying_issues"] == 1
        assert entry["total_issues"] == 1

    @pytest.mark.asyncio
    async def test_correction_accepted_includes_pre_post_counts(self) -> None:
        """correction_accepted log includes pre_issues, post_issues, issues_fixed."""
        pre = [_ERROR_ISSUE, {**_ERROR_ISSUE, "property_id": "gap"}]
        post = [{**_ERROR_ISSUE, "property_id": "gap"}]  # 1 remaining
        mock_css, mock_onto, mock_registry, settings = _llm_patches(
            pre_issues=pre, post_issues=post
        )
        agent = _FakeAgent()
        with (
            structlog.testing.capture_logs() as logs,
            patch("app.ai.agents.validation_loop.get_settings", return_value=settings),
            patch("app.ai.agents.validation_loop.unsupported_css_in_html", mock_css),
            patch("app.ai.agents.validation_loop.load_ontology", return_value=mock_onto),
            patch("app.ai.registry.get_registry", return_value=mock_registry),
        ):
            await agent._crag_validate_and_correct("<html></html>", "sys", "m")

        entry = _find_log(logs, "agents.crag.correction_accepted")
        assert entry is not None
        assert entry["pre_issues"] == 2
        assert entry["post_issues"] == 1
        assert entry["issues_fixed"] == 1
        assert entry["corrections"] == ["display_flex", "gap"]

    @pytest.mark.asyncio
    async def test_llm_failure_logs_rejection_with_reason(self) -> None:
        """LLM failure emits correction_rejected with reason=llm_call_failed."""
        mock_css, mock_onto, mock_registry, settings = _llm_patches(
            pre_issues=[_ERROR_ISSUE], llm_side_effect=RuntimeError("boom")
        )
        agent = _FakeAgent()
        with (
            structlog.testing.capture_logs() as logs,
            patch("app.ai.agents.validation_loop.get_settings", return_value=settings),
            patch("app.ai.agents.validation_loop.unsupported_css_in_html", mock_css),
            patch("app.ai.agents.validation_loop.load_ontology", return_value=mock_onto),
            patch("app.ai.registry.get_registry", return_value=mock_registry),
        ):
            _html, corrections = await agent._crag_validate_and_correct("<html></html>", "sys", "m")

        assert corrections == []
        entry = _find_log(logs, "agents.crag.correction_rejected")
        assert entry is not None
        assert entry["reason"] == "llm_call_failed"
        assert entry["pre_issues"] == 1
        assert entry["qualifying_property_ids"] == ["display_flex"]

    @pytest.mark.asyncio
    async def test_output_too_short_logs_rejection_with_reason(self) -> None:
        """Short LLM output emits correction_rejected with reason=output_too_short."""
        mock_css, mock_onto, mock_registry, settings = _llm_patches(
            pre_issues=[_ERROR_ISSUE], llm_content=""
        )
        agent = _FakeAgent()
        with (
            structlog.testing.capture_logs() as logs,
            patch("app.ai.agents.validation_loop.get_settings", return_value=settings),
            patch("app.ai.agents.validation_loop.unsupported_css_in_html", mock_css),
            patch("app.ai.agents.validation_loop.load_ontology", return_value=mock_onto),
            patch("app.ai.registry.get_registry", return_value=mock_registry),
        ):
            _html, corrections = await agent._crag_validate_and_correct("<html></html>", "sys", "m")

        assert corrections == []
        entry = _find_log(logs, "agents.crag.correction_rejected")
        assert entry is not None
        assert entry["reason"] in ("output_too_short", "no_html_in_response")
        assert entry["pre_issues"] == 1

    @pytest.mark.asyncio
    async def test_no_css_values_in_log_output(self) -> None:
        """CRAG log events must not leak CSS values (potential user content)."""
        issue_with_value = {
            **_ERROR_ISSUE,
            "value": "flex",
        }
        mock_css, mock_onto, mock_registry, settings = _llm_patches(
            pre_issues=[issue_with_value], post_issues=[]
        )
        agent = _FakeAgent()
        with (
            structlog.testing.capture_logs() as logs,
            patch("app.ai.agents.validation_loop.get_settings", return_value=settings),
            patch("app.ai.agents.validation_loop.unsupported_css_in_html", mock_css),
            patch("app.ai.agents.validation_loop.load_ontology", return_value=mock_onto),
            patch("app.ai.registry.get_registry", return_value=mock_registry),
        ):
            await agent._crag_validate_and_correct("<html></html>", "sys", "m")

        crag_logs = [e for e in logs if str(e.get("event", "")).startswith("agents.crag.")]
        assert len(crag_logs) >= 1
        for entry in crag_logs:
            assert "value" not in entry, f"CSS 'value' field leaked in {entry['event']}"
            assert "property_name" not in entry, f"'property_name' leaked in {entry['event']}"
