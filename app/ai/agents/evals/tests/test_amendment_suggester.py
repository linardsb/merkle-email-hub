"""Tests for amendment_suggester module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.evals.amendment_suggester import (
    _build_suggestion_prompt,
    _filter_actionable_clusters,
    _format_suggestion_file,
    _load_analysis,
    generate_suggestions,
)
from app.ai.protocols import CompletionResponse


def _make_cluster(
    agent: str = "scaffolder",
    criterion: str = "layout_accuracy",
    count: int = 5,
    pattern: str = "Tables not properly nested",
    sample_reasonings: list[str] | None = None,
) -> dict[str, object]:
    return {
        "cluster_id": f"{agent}:{criterion}",
        "agent": agent,
        "criterion": criterion,
        "pattern": pattern,
        "count": count,
        "trace_ids": [f"trace_{i}" for i in range(count)],
        "sample_reasonings": sample_reasonings or [f"Reasoning {i}" for i in range(min(count, 3))],
    }


# --- _load_analysis ---


def test_load_analysis_missing_file(tmp_path: Path) -> None:
    result = _load_analysis(tmp_path / "missing.json")
    assert result is None


def test_load_analysis_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json!!")
    result = _load_analysis(bad_file)
    assert result is None


def test_load_analysis_valid(tmp_path: Path) -> None:
    data = {"failure_clusters": [_make_cluster()]}
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(data))
    result = _load_analysis(f)
    assert result is not None
    assert len(result["failure_clusters"]) == 1


# --- _filter_actionable_clusters ---


def test_filter_actionable_clusters_below_threshold() -> None:
    clusters = [_make_cluster(count=2), _make_cluster(count=1)]
    result = _filter_actionable_clusters(clusters, min_size=3)
    assert result == {}


def test_filter_actionable_clusters_groups_by_agent() -> None:
    clusters = [
        _make_cluster(agent="scaffolder", criterion="layout", count=5),
        _make_cluster(agent="scaffolder", criterion="dark_mode", count=4),
        _make_cluster(agent="content", criterion="tone", count=3),
    ]
    result = _filter_actionable_clusters(clusters, min_size=3)
    assert len(result) == 2
    assert len(result["scaffolder"]) == 2
    assert len(result["content"]) == 1


def test_filter_actionable_clusters_empty() -> None:
    result = _filter_actionable_clusters([], min_size=3)
    assert result == {}


# --- _build_suggestion_prompt ---


def test_build_suggestion_prompt_contains_skill_and_clusters() -> None:
    skill_md = "# Scaffolder SKILL\nBuild email layouts."
    clusters = [_make_cluster(criterion="layout_accuracy", count=5)]
    prompt = _build_suggestion_prompt("scaffolder", skill_md, clusters)

    assert "scaffolder" in prompt
    assert "Build email layouts." in prompt
    assert "layout_accuracy" in prompt
    assert "5 failures" in prompt
    assert "Reasoning 0" in prompt


# --- _format_suggestion_file ---


def test_format_suggestion_file_structure() -> None:
    clusters = [_make_cluster(criterion="layout_accuracy", count=5)]
    llm_response = "### Failure Analysis\nThe agent fails because..."
    result = _format_suggestion_file("scaffolder", clusters, llm_response, "2026-03-16")

    assert "# SKILL.md Amendment Suggestions: scaffolder" in result
    assert "Generated: 2026-03-16" in result
    assert "## Failure Clusters Addressed" in result
    assert "**layout_accuracy**: 5 failures" in result
    assert "The agent fails because..." in result
    assert "`app/ai/agents/scaffolder/SKILL.md`" in result
    assert "Do NOT auto-merge" in result


# --- generate_suggestions (integration with mocks) ---


@pytest.mark.asyncio
async def test_generate_suggestions_no_analysis(tmp_path: Path) -> None:
    result = await generate_suggestions(
        analysis_path=tmp_path / "missing.json",
        output_dir=tmp_path / "out",
    )
    assert result == []


@pytest.mark.asyncio
async def test_generate_suggestions_no_actionable(tmp_path: Path) -> None:
    analysis = {"failure_clusters": [_make_cluster(count=1)]}
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(analysis))

    result = await generate_suggestions(
        analysis_path=f,
        output_dir=tmp_path / "out",
        min_cluster_size=3,
    )
    assert result == []


@pytest.mark.asyncio
async def test_generate_suggestions_writes_files(tmp_path: Path) -> None:
    analysis = {"failure_clusters": [_make_cluster(agent="scaffolder", count=5)]}
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(analysis))

    # Create a fake SKILL.md
    skill_dir = tmp_path / "skill_base" / "scaffolder"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Scaffolder\nBuild layouts.")

    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(
        return_value=CompletionResponse(
            content="### Failure Analysis\nAnalysis here.\n### Suggested SKILL.md Amendments\nAdd this.",
            model="test-model",
        )
    )

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider

    mock_settings = MagicMock()
    mock_settings.ai.provider = "test"

    out_dir = tmp_path / "suggestions"

    with (
        patch("app.ai.agents.evals.amendment_suggester.get_settings", return_value=mock_settings),
        patch("app.ai.agents.evals.amendment_suggester.get_registry", return_value=mock_registry),
        patch("app.ai.agents.evals.amendment_suggester.resolve_model", return_value="test-model"),
        patch("app.ai.agents.evals.amendment_suggester._SKILL_BASE", tmp_path / "skill_base"),
    ):
        result = await generate_suggestions(
            analysis_path=f,
            output_dir=out_dir,
            min_cluster_size=3,
        )

    assert len(result) == 1
    assert result[0].parent == out_dir
    assert "scaffolder_" in result[0].name
    content = result[0].read_text()
    assert "Analysis here." in content
    assert "Add this." in content


@pytest.mark.asyncio
async def test_generate_suggestions_skips_missing_skill(tmp_path: Path) -> None:
    analysis = {"failure_clusters": [_make_cluster(agent="nonexistent_agent", count=5)]}
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(analysis))

    mock_provider = MagicMock()
    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider
    mock_settings = MagicMock()
    mock_settings.ai.provider = "test"

    with (
        patch("app.ai.agents.evals.amendment_suggester.get_settings", return_value=mock_settings),
        patch("app.ai.agents.evals.amendment_suggester.get_registry", return_value=mock_registry),
        patch("app.ai.agents.evals.amendment_suggester.resolve_model", return_value="test-model"),
        patch("app.ai.agents.evals.amendment_suggester._SKILL_BASE", tmp_path / "skill_base"),
    ):
        result = await generate_suggestions(
            analysis_path=f,
            output_dir=tmp_path / "out",
            min_cluster_size=3,
        )

    assert result == []


@pytest.mark.asyncio
async def test_generate_suggestions_handles_llm_error(tmp_path: Path) -> None:
    # Two agents: one will fail LLM, one will succeed
    analysis = {
        "failure_clusters": [
            _make_cluster(agent="scaffolder", count=5),
            _make_cluster(agent="content", count=4),
        ]
    }
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(analysis))

    # Create SKILL.md for both
    for name in ("scaffolder", "content"):
        d = tmp_path / "skill_base" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {name}\nSkill content.")

    call_count = 0

    async def mock_complete(*args: object, **kwargs: object) -> CompletionResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("LLM timeout")
        return CompletionResponse(content="### Suggestion\nDo this.", model="test")

    mock_provider = MagicMock()
    mock_provider.complete = mock_complete

    mock_registry = MagicMock()
    mock_registry.get_llm.return_value = mock_provider
    mock_settings = MagicMock()
    mock_settings.ai.provider = "test"

    with (
        patch("app.ai.agents.evals.amendment_suggester.get_settings", return_value=mock_settings),
        patch("app.ai.agents.evals.amendment_suggester.get_registry", return_value=mock_registry),
        patch("app.ai.agents.evals.amendment_suggester.resolve_model", return_value="test-model"),
        patch("app.ai.agents.evals.amendment_suggester._SKILL_BASE", tmp_path / "skill_base"),
    ):
        result = await generate_suggestions(
            analysis_path=f,
            output_dir=tmp_path / "out",
            min_cluster_size=3,
        )

    # Sorted alphabetically: content (fails LLM) < scaffolder (succeeds)
    assert len(result) == 1
