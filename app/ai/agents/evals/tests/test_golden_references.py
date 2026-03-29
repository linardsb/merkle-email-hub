"""Tests for golden reference loader and criterion mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from app.ai.agents.evals.golden_references import (
    _GOLDEN_REF_DIR,
    _MAX_SNIPPET_LINES,
    _extract_snippet,
    get_references_for_agent,
    get_references_for_criterion,
    load_golden_references,
)
from app.ai.agents.evals.judge_criteria_map import JUDGE_CRITERIA_MAP
from app.ai.agents.evals.judges import JUDGE_REGISTRY
from app.core.exceptions import DomainValidationError, NotFoundError


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear lru_cache between tests."""
    load_golden_references.cache_clear()


class TestLoadGoldenReferences:
    def test_discovers_all(self) -> None:
        refs = load_golden_references()
        assert len(refs) == 14

    def test_each_reference_has_required_fields(self) -> None:
        for ref in load_golden_references():
            assert ref.name, f"Missing name on {ref.source_file}"
            assert ref.html, f"Missing html on {ref.name}"
            assert ref.criteria, f"Missing criteria on {ref.name}"
            assert ref.agents, f"Missing agents on {ref.name}"
            assert ref.verified_date, f"Missing verified_date on {ref.name}"
            assert ref.source_file, f"Missing source_file on {ref.name}"

    def test_criteria_are_valid_judge_criteria(self) -> None:
        all_criteria: set[str] = set()
        for mappings in JUDGE_CRITERIA_MAP.values():
            for m in mappings:
                all_criteria.add(m.criterion)
        for ref in load_golden_references():
            for c in ref.criteria:
                assert c in all_criteria, f"Unknown criterion '{c}' in {ref.name}"

    def test_agents_are_valid_agent_names(self) -> None:
        valid_agents = set(JUDGE_REGISTRY.keys())
        for ref in load_golden_references():
            for a in ref.agents:
                assert a in valid_agents, f"Unknown agent '{a}' in {ref.name}"

    def test_returns_tuple(self) -> None:
        refs = load_golden_references()
        assert isinstance(refs, tuple)

    def test_references_are_frozen(self) -> None:
        ref = load_golden_references()[0]
        with pytest.raises(AttributeError):
            ref.name = "changed"  # type: ignore[misc]


class TestGetReferencesForCriterion:
    def test_mso_conditional_correctness(self) -> None:
        results = get_references_for_criterion("mso_conditional_correctness")
        assert len(results) >= 2
        names = {name for name, _ in results}
        assert "VML Background Image" in names or "Nested MSO Conditionals" in names

    def test_vml_wellformedness(self) -> None:
        results = get_references_for_criterion("vml_wellformedness")
        assert len(results) >= 2

    def test_unknown_criterion_returns_empty(self) -> None:
        assert get_references_for_criterion("nonexistent_criterion") == []

    def test_budget_cap_max_3(self) -> None:
        for ref in load_golden_references():
            for c in ref.criteria:
                results = get_references_for_criterion(c)
                assert len(results) <= 3, f"Criterion '{c}' returned {len(results)} snippets"


class TestGetReferencesForAgent:
    def test_outlook_fixer(self) -> None:
        results = get_references_for_agent("outlook_fixer")
        assert len(results) >= 2
        names = {r.name for r in results}
        assert "VML Background Image" in names

    def test_unknown_agent_returns_empty(self) -> None:
        assert get_references_for_agent("nonexistent_agent") == []


class TestSnippetExtraction:
    def test_respects_line_cap(self) -> None:
        for ref in load_golden_references():
            line_count = len(ref.html.splitlines())
            assert line_count <= _MAX_SNIPPET_LINES, (
                f"{ref.name}: {line_count} lines exceeds cap of {_MAX_SNIPPET_LINES}"
            )

    def test_selector_extracts_range(self) -> None:
        index_path = _GOLDEN_REF_DIR / "index.yaml"
        raw: dict[str, Any] = yaml.safe_load(index_path.read_text())
        for entry in raw["references"]:
            if "selector" in entry and "lines" in entry["selector"]:
                start, end = entry["selector"]["lines"]
                expected_count = min(end - start + 1, _MAX_SNIPPET_LINES)
                ref = next(r for r in load_golden_references() if r.source_file == entry["file"])
                actual_count = len(ref.html.splitlines())
                assert actual_count == expected_count, (
                    f"{entry['name']}: expected {expected_count} lines, got {actual_count}"
                )
                break  # one verification is sufficient


class TestCache:
    def test_returns_same_object(self) -> None:
        first = load_golden_references()
        second = load_golden_references()
        assert first is second


class TestSecurity:
    def test_path_traversal_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="path traversal"):
            _extract_snippet("../../etc/passwd", None)

    def test_slash_in_filename_rejected(self) -> None:
        with pytest.raises(DomainValidationError, match="path traversal"):
            _extract_snippet("subdir/file.html", None)

    def test_missing_index_raises_not_found(self, tmp_path: Path) -> None:
        with patch(
            "app.ai.agents.evals.golden_references._INDEX_FILE",
            tmp_path / "nonexistent.yaml",
        ):
            with pytest.raises(NotFoundError, match="index not found"):
                load_golden_references()
