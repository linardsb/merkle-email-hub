"""Tests for the visual defect correction service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.visual_qa.correction import correct_visual_defects
from app.ai.agents.visual_qa.decisions import DetectedDefect


def _make_defect(
    *,
    region: str = "header",
    css_property: str = "display: flex",
    suggested_fix: str = "Use table layout",
    severity: str = "warning",
    affected_clients: tuple[str, ...] = ("outlook_2019",),
) -> DetectedDefect:
    return DetectedDefect(
        region=region,
        description=f"Broken {region}",
        severity=severity,
        affected_clients=affected_clients,
        suggested_fix=suggested_fix,
        css_property=css_property,
    )


MINIMAL_HTML = "<html><body><table><tr><td>Hello</td></tr></table></body></html>"


@pytest.mark.asyncio
async def test_no_fixable_defects_returns_original() -> None:
    """Defects without css_property or suggested_fix are skipped."""
    defect = DetectedDefect(
        region="header",
        description="looks off",
        severity="info",
        affected_clients=("gmail_web",),
        suggested_fix="",
        css_property="",
    )
    result_html, corrections = await correct_visual_defects(MINIMAL_HTML, (defect,), "gpt-4o")
    assert result_html == MINIMAL_HTML
    assert corrections == []


@pytest.mark.asyncio
async def test_correction_with_ontology_fallback() -> None:
    """Defect with css_property triggers ontology lookup + LLM correction."""
    defect = _make_defect(css_property="display: flex")

    mock_result = MagicMock()
    mock_result.content = f"```html\n{MINIMAL_HTML}\n```"

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value=mock_result)

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        result_html, corrections = await correct_visual_defects(MINIMAL_HTML, (defect,), "gpt-4o")

    assert "Hello" in result_html  # Content preserved through sanitize pipeline
    assert len(corrections) == 1
    assert "header" in corrections[0]
    mock_provider.complete.assert_called_once()


@pytest.mark.asyncio
async def test_correction_with_suggested_fix_only() -> None:
    """Defect without css_property uses VLM's suggested_fix."""
    defect = _make_defect(css_property="", suggested_fix="Add width:100% to container")

    mock_result = MagicMock()
    mock_result.content = f"```html\n{MINIMAL_HTML}\n```"

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value=mock_result)

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        _result_html, corrections = await correct_visual_defects(MINIMAL_HTML, (defect,), "gpt-4o")

    assert len(corrections) == 1
    # Verify prompt includes suggested_fix
    call_args = mock_provider.complete.call_args
    user_msg = call_args[0][0][1].content
    assert "Add width:100%" in user_msg


@pytest.mark.asyncio
async def test_llm_failure_returns_original() -> None:
    """LLM exception -> return original HTML unchanged."""
    defect = _make_defect()

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(side_effect=RuntimeError("LLM down"))

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        result_html, corrections = await correct_visual_defects(MINIMAL_HTML, (defect,), "gpt-4o")

    assert result_html == MINIMAL_HTML
    assert corrections == []


@pytest.mark.asyncio
async def test_empty_llm_output_returns_original() -> None:
    """LLM returns empty/too-short output -> failure-safe."""
    defect = _make_defect()

    mock_result = MagicMock()
    mock_result.content = "sorry"

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value=mock_result)

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        result_html, corrections = await correct_visual_defects(MINIMAL_HTML, (defect,), "gpt-4o")

    assert result_html == MINIMAL_HTML
    assert corrections == []


@pytest.mark.asyncio
async def test_multiple_defects_all_included() -> None:
    """Multiple fixable defects -> all included in correction prompt."""
    defects = (
        _make_defect(region="header", css_property="display: flex"),
        _make_defect(region="footer", css_property="gap: 16px"),
        _make_defect(region="cta", css_property="", suggested_fix="Use padding instead"),
    )

    mock_result = MagicMock()
    mock_result.content = f"```html\n{MINIMAL_HTML}\n```"

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value=mock_result)

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        _result_html, corrections = await correct_visual_defects(MINIMAL_HTML, defects, "gpt-4o")

    assert len(corrections) == 3
    call_args = mock_provider.complete.call_args
    user_msg = call_args[0][0][1].content
    assert "header" in user_msg
    assert "footer" in user_msg
    assert "cta" in user_msg


@pytest.mark.asyncio
async def test_html_capped_at_100k() -> None:
    """Large HTML is capped at 100K in the correction prompt."""
    large_html = "<html>" + "x" * 150_000 + "</html>"
    defect = _make_defect()

    mock_result = MagicMock()
    mock_result.content = f"```html\n{MINIMAL_HTML}\n```"

    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(return_value=mock_result)

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    with (
        patch("app.ai.agents.visual_qa.correction.get_registry", return_value=mock_registry),
        patch("app.ai.agents.visual_qa.correction.get_settings") as mock_settings,
    ):
        mock_settings.return_value.ai.provider = "openai"
        await correct_visual_defects(large_html, (defect,), "gpt-4o")

    call_args = mock_provider.complete.call_args
    user_msg = call_args[0][0][1].content
    # Prompt should not contain full 150K HTML
    assert len(user_msg) < 120_000
