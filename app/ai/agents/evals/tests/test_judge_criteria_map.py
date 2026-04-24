"""Tests for deterministic micro-judges (judge criteria → QA check mapping)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from app.ai.agents.evals.judge_criteria_map import (
    JUDGE_CRITERIA_MAP,
    CriteriaMapping,
    build_coverage_report,
    compute_coverage,
    evaluate_criterion_via_qa,
    get_all_qa_check_names,
    get_llm_only_criteria,
    get_mapped_criteria,
)
from app.ai.agents.evals.judges.schemas import CriterionResult

# ── Mapping Completeness ────────────────────────────────────────────────


class TestMappingCompleteness:
    """Verify the static mapping covers all agents and criteria."""

    EXPECTED_AGENTS: ClassVar[list[str]] = [
        "scaffolder",
        "dark_mode",
        "content",
        "outlook_fixer",
        "accessibility",
        "personalisation",
        "code_reviewer",
        "knowledge",
        "innovation",
    ]

    def test_all_agents_mapped(self) -> None:
        """Every agent in JUDGE_REGISTRY has a mapping entry."""
        for agent in self.EXPECTED_AGENTS:
            assert agent in JUDGE_CRITERIA_MAP, f"Missing mapping for agent: {agent}"

    # Agents with extended criteria (beyond the base 5)
    EXTENDED_CRITERIA_AGENTS: ClassVar[dict[str, int]] = {
        "scaffolder": 6,  # +design_fidelity
    }

    def test_each_agent_has_expected_criteria_count(self) -> None:
        """Each agent must have the expected number of criteria mapped."""
        for agent, mappings in JUDGE_CRITERIA_MAP.items():
            expected = self.EXTENDED_CRITERIA_AGENTS.get(agent, 5)
            assert len(mappings) == expected, (
                f"{agent} has {len(mappings)} criteria, expected {expected}"
            )

    def test_no_duplicate_criteria_per_agent(self) -> None:
        """No agent should have duplicate criterion names."""
        for agent, mappings in JUDGE_CRITERIA_MAP.items():
            names = [m.criterion for m in mappings]
            assert len(names) == len(set(names)), f"{agent} has duplicate criteria: {names}"

    def test_criteria_names_match_judges(self) -> None:
        """Criterion names in map must match actual judge criteria names."""
        from app.ai.agents.evals.judges import JUDGE_REGISTRY

        for agent, mappings in JUDGE_CRITERIA_MAP.items():
            judge_cls = JUDGE_REGISTRY.get(agent)
            if judge_cls is None:
                continue
            judge = judge_cls()
            judge_criteria_names = {c.name for c in judge.criteria}
            map_criteria_names = {m.criterion for m in mappings}
            assert map_criteria_names == judge_criteria_names, (
                f"{agent}: map has {map_criteria_names}, judge has {judge_criteria_names}"
            )

    def test_qa_check_names_are_valid(self) -> None:
        """All referenced QA check names must exist in ALL_CHECKS."""
        from app.qa_engine.checks import ALL_CHECKS

        valid_names = {c.name for c in ALL_CHECKS}
        referenced = get_all_qa_check_names()
        invalid = referenced - valid_names
        assert not invalid, f"Invalid QA check names in mapping: {invalid}"


# ── Coverage Helpers ────────────────────────────────────────────────────


class TestCoverageHelpers:
    """Test coverage computation functions."""

    def test_get_mapped_criteria_scaffolder(self) -> None:
        mapped = get_mapped_criteria("scaffolder")
        assert len(mapped) == 4  # brief_fidelity is LLM-only
        names = {m.criterion for m in mapped}
        assert "brief_fidelity" not in names

    def test_get_llm_only_criteria_scaffolder(self) -> None:
        llm_only = get_llm_only_criteria("scaffolder")
        assert len(llm_only) == 2
        names = {m.criterion for m in llm_only}
        assert names == {"brief_fidelity", "design_fidelity"}

    def test_get_mapped_criteria_content(self) -> None:
        mapped = get_mapped_criteria("content")
        assert len(mapped) == 1  # Only spam_avoidance
        assert mapped[0].criterion == "spam_avoidance"

    def test_get_mapped_criteria_accessibility(self) -> None:
        mapped = get_mapped_criteria("accessibility")
        assert len(mapped) == 5  # All 5 mapped

    def test_compute_coverage_totals(self) -> None:
        summaries = compute_coverage()
        total = sum(s.total_criteria for s in summaries)
        assert total == 46  # 8 agents x 5 + scaffolder x 6

    def test_compute_coverage_mapped_count(self) -> None:
        summaries = compute_coverage()
        mapped = sum(s.mapped_criteria for s in summaries)
        assert mapped == 27  # Based on current mapping


# ── Multi-Check Strategy ────────────────────────────────────────────────


class TestMultiCheckStrategy:
    """Test the ALL strategy for multi-check mappings."""

    @pytest.mark.asyncio
    async def test_all_strategy_requires_all_checks_pass(self) -> None:
        """With strategy='all', criterion fails if any QA check fails."""
        # Use screen_reader_compatibility which maps to accessibility + fallback
        mapping = CriteriaMapping(
            criterion="screen_reader_compatibility",
            qa_checks=["accessibility", "fallback"],
            strategy="all",
        )
        # Minimal HTML that should fail at least one check
        html = "<html><body><p>test</p></body></html>"
        result = await evaluate_criterion_via_qa(html, mapping)
        assert isinstance(result, CriterionResult)
        assert result.criterion == "screen_reader_compatibility"
        assert "[DETERMINISTIC]" in result.reasoning


# ── Coverage Report ─────────────────────────────────────────────────────


class TestCoverageReport:
    """Test report generation."""

    def test_build_report_structure(self) -> None:
        summaries = compute_coverage()
        report = build_coverage_report(summaries)
        assert "total_criteria" in report
        assert "total_mapped" in report
        assert "overall_coverage_pct" in report
        assert "agents" in report
        assert len(report["agents"]) == 9

    def test_report_coverage_percentage(self) -> None:
        summaries = compute_coverage()
        report = build_coverage_report(summaries)
        assert report["overall_coverage_pct"] == pytest.approx(58.7, abs=0.1)  # pyright: ignore[reportUnknownMemberType] # 27/46

    def test_report_agent_detail(self) -> None:
        summaries = compute_coverage()
        report = build_coverage_report(summaries)
        scaffolder = next(a for a in report["agents"] if a["agent"] == "scaffolder")
        assert scaffolder["mapped"] == 4
        assert scaffolder["llm_only"] == 2
        assert scaffolder["coverage_pct"] == pytest.approx(66.7, abs=0.1)  # pyright: ignore[reportUnknownMemberType]
