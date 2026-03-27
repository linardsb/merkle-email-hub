"""Tests for eval-driven skill file update detector and patch generator."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.evals.schemas import SkillFilePatch, SkillUpdateCandidate
from app.ai.agents.evals.skill_updater import (
    CRITERION_SKILL_MAP,
    SkillUpdateDetector,
    _resolve_skill_file,
    apply_patches,
    format_candidate_report,
    format_patch_report,
)
from app.ai.protocols import CompletionResponse

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_analysis(
    pass_rates: dict[str, dict[str, float]] | None = None,
    failure_clusters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "summary": {
            "total_traces": 10,
            "passed": 5,
            "failed": 5,
            "errors": 0,
            "overall_pass_rate": 0.5,
        },
        "pass_rates": pass_rates or {},
        "failure_clusters": failure_clusters or [],
        "top_failures": [],
    }


def _make_cluster(
    agent: str = "scaffolder",
    criterion: str = "mso_conditionals",
    count: int = 7,
    pattern: str = "Missing MSO conditional wrappers",
    sample_reasonings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "cluster_id": f"{agent}:{criterion}",
        "agent": agent,
        "criterion": criterion,
        "pattern": pattern,
        "count": count,
        "trace_ids": [f"t{i}" for i in range(count)],
        "sample_reasonings": sample_reasonings
        or [f"Fail reason {i}" for i in range(min(count, 3))],
    }


def _write_analysis(tmp_path: Path, data: dict[str, Any]) -> Path:
    f = tmp_path / "analysis.json"
    f.write_text(json.dumps(data))
    return f


# ---------------------------------------------------------------------------
# detect_update_candidates
# ---------------------------------------------------------------------------


class TestDetectUpdateCandidates:
    def test_no_analysis_file(self, tmp_path: Path) -> None:
        detector = SkillUpdateDetector(analysis_path=tmp_path / "missing.json")
        assert detector.detect_update_candidates() == []

    def test_no_candidates_all_passing(self, tmp_path: Path) -> None:
        data = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.95, "brief_fidelity": 0.88}},
        )
        path = _write_analysis(tmp_path, data)
        detector = SkillUpdateDetector(analysis_path=path)
        assert detector.detect_update_candidates() == []

    def test_candidates_below_threshold(self, tmp_path: Path) -> None:
        cluster = _make_cluster(agent="scaffolder", criterion="mso_conditionals", count=7)
        data = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.58}},
            failure_clusters=[cluster],
        )
        path = _write_analysis(tmp_path, data)
        detector = SkillUpdateDetector(analysis_path=path)
        candidates = detector.detect_update_candidates()

        assert len(candidates) == 1
        assert candidates[0].agent == "scaffolder"
        assert candidates[0].criterion == "mso_conditionals"
        assert candidates[0].pass_rate == 0.58
        assert candidates[0].failure_count == 7
        assert candidates[0].source == "eval"

    def test_ignores_low_count(self, tmp_path: Path) -> None:
        cluster = _make_cluster(agent="scaffolder", criterion="mso_conditionals", count=2)
        data = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.50}},
            failure_clusters=[cluster],
        )
        path = _write_analysis(tmp_path, data)
        detector = SkillUpdateDetector(analysis_path=path, min_failures=5)
        assert detector.detect_update_candidates() == []

    def test_sorting_by_impact(self, tmp_path: Path) -> None:
        clusters = [
            _make_cluster(agent="scaffolder", criterion="code_quality", count=5),
            _make_cluster(agent="scaffolder", criterion="mso_conditionals", count=10),
        ]
        data = _make_analysis(
            pass_rates={
                "scaffolder": {
                    "code_quality": 0.70,
                    "mso_conditionals": 0.40,
                },
            },
            failure_clusters=clusters,
        )
        path = _write_analysis(tmp_path, data)
        detector = SkillUpdateDetector(analysis_path=path)
        candidates = detector.detect_update_candidates()

        assert len(candidates) == 2
        # Lowest pass rate first
        assert candidates[0].criterion == "mso_conditionals"
        assert candidates[1].criterion == "code_quality"

    def test_agent_filter(self, tmp_path: Path) -> None:
        clusters = [
            _make_cluster(agent="scaffolder", criterion="mso_conditionals", count=6),
            _make_cluster(agent="dark_mode", criterion="color_coherence", count=8),
        ]
        data = _make_analysis(
            pass_rates={
                "scaffolder": {"mso_conditionals": 0.50},
                "dark_mode": {"color_coherence": 0.40},
            },
            failure_clusters=clusters,
        )
        path = _write_analysis(tmp_path, data)
        detector = SkillUpdateDetector(analysis_path=path)
        candidates = detector.detect_update_candidates(agent_filter="scaffolder")

        assert len(candidates) == 1
        assert candidates[0].agent == "scaffolder"

    def test_threshold_override(self, tmp_path: Path) -> None:
        cluster = _make_cluster(agent="scaffolder", criterion="mso_conditionals", count=6)
        data = _make_analysis(
            pass_rates={"scaffolder": {"mso_conditionals": 0.85}},
            failure_clusters=[cluster],
        )
        path = _write_analysis(tmp_path, data)

        # Default threshold 0.80 — would NOT detect this
        detector_default = SkillUpdateDetector(analysis_path=path)
        assert detector_default.detect_update_candidates() == []

        # Higher threshold 0.90 — should detect it
        detector_strict = SkillUpdateDetector(analysis_path=path, threshold=0.90)
        candidates = detector_strict.detect_update_candidates()
        assert len(candidates) == 1


# ---------------------------------------------------------------------------
# CRITERION_SKILL_MAP coverage
# ---------------------------------------------------------------------------


class TestCriterionSkillMap:
    def test_all_nine_agents_mapped(self) -> None:
        expected_agents = {
            "scaffolder",
            "dark_mode",
            "content",
            "outlook_fixer",
            "accessibility",
            "personalisation",
            "code_reviewer",
            "knowledge",
            "innovation",
        }
        assert set(CRITERION_SKILL_MAP.keys()) == expected_agents

    def test_each_agent_has_five_criteria(self) -> None:
        for agent, criteria in CRITERION_SKILL_MAP.items():
            assert len(criteria) == 5, f"{agent} has {len(criteria)} criteria, expected 5"

    def test_all_mapped_files_exist(self) -> None:
        """Verify every criterion maps to a real L3 skill file on disk."""
        base = Path("app/ai/agents")
        for agent, criteria in CRITERION_SKILL_MAP.items():
            for criterion, filename in criteria.items():
                skill_path = base / agent / "skills" / filename
                assert skill_path.exists(), (
                    f"Missing skill file: {skill_path} (mapped from {agent}:{criterion})"
                )

    def test_fallback_to_skill_md(self) -> None:
        result = _resolve_skill_file("scaffolder", "unknown_criterion")
        assert result.endswith("SKILL.md")


# ---------------------------------------------------------------------------
# generate_patch
# ---------------------------------------------------------------------------


class TestGeneratePatch:
    @pytest.mark.asyncio
    async def test_calls_llm(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "app" / "ai" / "agents" / "scaffolder" / "skills"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "mso_vml_quick_ref.md"
        skill_file.write_text("# MSO VML Quick Reference\nExisting content here.")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.58,
            failure_count=7,
            failure_cluster="Missing MSO wrappers",
            sample_reasons=["Fail 1", "Fail 2"],
            target_skill_file=str(skill_file),
        )

        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(
            return_value=CompletionResponse(
                content=(
                    "### PATCH_START\n"
                    "## MSO Wrapper Checklist\n"
                    "Always wrap tables in MSO conditionals.\n"
                    "### PATCH_END\n"
                    "\n### CONFIDENCE\nHIGH"
                ),
                model="test-model",
            )
        )
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider
        mock_settings = MagicMock()
        mock_settings.ai.provider = "test"

        detector = SkillUpdateDetector()
        with (
            patch(
                "app.ai.agents.evals.skill_updater.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.get_registry",
                return_value=mock_registry,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.resolve_model",
                return_value="test-model",
            ),
        ):
            patch_result = await detector.generate_patch(candidate)

        assert patch_result is not None
        assert "MSO Wrapper Checklist" in patch_result.patch_content
        assert patch_result.confidence == "HIGH"
        assert patch_result.candidate == candidate

        # Verify LLM was called
        mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Skill\nContent.")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )

        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider
        mock_settings = MagicMock()
        mock_settings.ai.provider = "test"

        detector = SkillUpdateDetector()
        with (
            patch(
                "app.ai.agents.evals.skill_updater.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.get_registry",
                return_value=mock_registry,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.resolve_model",
                return_value="test-model",
            ),
        ):
            result = await detector.generate_patch(candidate)

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_skill_file_returns_none(self) -> None:
        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file="/nonexistent/path.md",
        )
        detector = SkillUpdateDetector()
        result = await detector.generate_patch(candidate)
        assert result is None

    @pytest.mark.asyncio
    async def test_duplicate_content_skipped(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Skill\nAlways wrap tables in MSO conditionals.")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )

        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(
            return_value=CompletionResponse(
                content=(
                    "### PATCH_START\n"
                    "Always wrap tables in MSO conditionals.\n"
                    "### PATCH_END\n"
                    "\n### CONFIDENCE\nLOW"
                ),
                model="test-model",
            )
        )
        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider
        mock_settings = MagicMock()
        mock_settings.ai.provider = "test"

        detector = SkillUpdateDetector()
        with (
            patch(
                "app.ai.agents.evals.skill_updater.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.get_registry",
                return_value=mock_registry,
            ),
            patch(
                "app.ai.agents.evals.skill_updater.resolve_model",
                return_value="test-model",
            ),
        ):
            result = await detector.generate_patch(candidate)

        assert result is None


# ---------------------------------------------------------------------------
# apply_patches
# ---------------------------------------------------------------------------


class TestApplyPatches:
    def test_dry_run_no_git(self, tmp_path: Path) -> None:
        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(tmp_path / "skill.md"),
        )
        patches = [
            SkillFilePatch(
                skill_file_path=str(tmp_path / "skill.md"),
                patch_content="New content",
                candidate=candidate,
            )
        ]
        result = apply_patches(patches, dry_run=True)
        assert result is None

    def test_empty_patches(self) -> None:
        result = apply_patches([], dry_run=False)
        assert result is None

    def test_git_commands_executed(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Existing\nContent here.\n")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )
        patches = [
            SkillFilePatch(
                skill_file_path=str(skill_file),
                patch_content="## New Section\nNew guidance.",
                candidate=candidate,
            )
        ]

        with patch("app.ai.agents.evals.skill_updater.subprocess") as mock_sub:
            mock_sub.run.return_value = CompletedProcess(args=[], returncode=0)
            branch = apply_patches(patches, dry_run=False)

        assert branch is not None
        assert branch.startswith("skill-update/scaffolder/mso_conditionals/")

        # Verify git calls: checkout -b, add, commit
        calls = mock_sub.run.call_args_list
        assert len(calls) == 3

        checkout_args = calls[0][0][0]
        assert checkout_args[:3] == ["git", "checkout", "-b"]

        add_args = calls[1][0][0]
        assert add_args[:2] == ["git", "add"]

        commit_args = calls[2][0][0]
        assert commit_args[:3] == ["git", "commit", "-m"]
        assert "eval-driven" in commit_args[3]

    def test_creates_branch_name(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("Content\n")

        candidate = SkillUpdateCandidate(
            agent="dark_mode",
            criterion="color_coherence",
            pass_rate=0.40,
            failure_count=10,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )
        patches = [
            SkillFilePatch(
                skill_file_path=str(skill_file),
                patch_content="Patch",
                candidate=candidate,
            )
        ]

        with patch("app.ai.agents.evals.skill_updater.subprocess") as mock_sub:
            mock_sub.run.return_value = CompletedProcess(args=[], returncode=0)
            branch = apply_patches(patches)

        assert branch is not None
        assert "dark_mode" in branch
        assert "color_coherence" in branch

    def test_appends_content_to_file(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("# Existing\nContent here.\n")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )
        patches = [
            SkillFilePatch(
                skill_file_path=str(skill_file),
                patch_content="## New Section\nNew guidance.",
                candidate=candidate,
            )
        ]

        with patch("app.ai.agents.evals.skill_updater.subprocess") as mock_sub:
            mock_sub.run.return_value = CompletedProcess(args=[], returncode=0)
            apply_patches(patches)

        content = skill_file.read_text()
        assert "# Existing" in content
        assert "## New Section" in content
        assert "New guidance." in content

    def test_git_failure_returns_none(self, tmp_path: Path) -> None:
        skill_file = tmp_path / "skill.md"
        skill_file.write_text("Content\n")

        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.50,
            failure_count=7,
            failure_cluster="Pattern",
            target_skill_file=str(skill_file),
        )
        patches = [
            SkillFilePatch(
                skill_file_path=str(skill_file),
                patch_content="Patch",
                candidate=candidate,
            )
        ]

        with patch("app.ai.agents.evals.skill_updater.subprocess") as mock_sub:
            mock_sub.CalledProcessError = subprocess.CalledProcessError
            mock_sub.run.side_effect = subprocess.CalledProcessError(
                1, ["git", "checkout", "-b", "branch"], stderr=b"branch already exists"
            )
            result = apply_patches(patches)

        assert result is None


# ---------------------------------------------------------------------------
# Tool usage promotion
# ---------------------------------------------------------------------------


class TestToolUsagePromotion:
    def test_promotion_candidates(self, tmp_path: Path) -> None:
        # Create tool_usage.jsonl with frequent queries
        tool_log = tmp_path / "tool_usage.jsonl"
        entries = [
            json.dumps({"agent": "scaffolder", "property": "css_support", "client": "outlook"})
            for _ in range(12)
        ]
        tool_log.write_text("\n".join(entries))

        analysis = _make_analysis()
        analysis_path = _write_analysis(tmp_path, analysis)

        detector = SkillUpdateDetector(
            analysis_path=analysis_path,
            tool_usage_path=tool_log,
        )
        candidates = detector.detect_update_candidates()

        promo = [c for c in candidates if c.source == "tool_usage"]
        assert len(promo) == 1
        assert "css_support" in promo[0].criterion
        assert promo[0].target_skill_file.endswith("SKILL.md")

    def test_no_tool_usage_file(self, tmp_path: Path) -> None:
        analysis = _make_analysis()
        analysis_path = _write_analysis(tmp_path, analysis)

        detector = SkillUpdateDetector(
            analysis_path=analysis_path,
            tool_usage_path=tmp_path / "nonexistent.jsonl",
        )
        candidates = detector.detect_update_candidates()
        assert candidates == []

    def test_below_promotion_threshold(self, tmp_path: Path) -> None:
        tool_log = tmp_path / "tool_usage.jsonl"
        entries = [
            json.dumps({"agent": "scaffolder", "property": "css_support", "client": "outlook"})
            for _ in range(5)  # Below threshold of 10
        ]
        tool_log.write_text("\n".join(entries))

        analysis = _make_analysis()
        analysis_path = _write_analysis(tmp_path, analysis)

        detector = SkillUpdateDetector(
            analysis_path=analysis_path,
            tool_usage_path=tool_log,
        )
        candidates = detector.detect_update_candidates()
        promo = [c for c in candidates if c.source == "tool_usage"]
        assert promo == []


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


class TestFormatting:
    def test_candidate_report_empty(self) -> None:
        assert "No skill update candidates" in format_candidate_report([])

    def test_candidate_report_with_candidates(self) -> None:
        candidates = [
            SkillUpdateCandidate(
                agent="scaffolder",
                criterion="mso_conditionals",
                pass_rate=0.58,
                failure_count=7,
                failure_cluster="Missing MSO wrappers",
                target_skill_file="app/ai/agents/scaffolder/skills/mso_vml_quick_ref.md",
            ),
        ]
        report = format_candidate_report(candidates)
        assert "scaffolder" in report
        assert "mso_conditionals" in report
        assert "58%" in report

    def test_patch_report_empty(self) -> None:
        assert "No patches generated" in format_patch_report([])

    def test_patch_report_with_patches(self) -> None:
        candidate = SkillUpdateCandidate(
            agent="scaffolder",
            criterion="mso_conditionals",
            pass_rate=0.58,
            failure_count=7,
            failure_cluster="Pattern",
        )
        patches = [
            SkillFilePatch(
                skill_file_path="app/ai/agents/scaffolder/skills/mso_vml_quick_ref.md",
                patch_content="## New guidance\nDo this.",
                candidate=candidate,
                confidence="HIGH",
            ),
        ]
        report = format_patch_report(patches)
        assert "mso_vml_quick_ref.md" in report
        assert "HIGH" in report
        assert "New guidance" in report


# ---------------------------------------------------------------------------
# Parse patch response
# ---------------------------------------------------------------------------


class TestParsePatchResponse:
    def test_structured_response(self) -> None:
        response = (
            "### PATCH_START\n"
            "## Check MSO wrappers\n"
            "Always validate.\n"
            "### PATCH_END\n"
            "\n### CONFIDENCE\nHIGH"
        )
        content, confidence = SkillUpdateDetector._parse_patch_response(response)
        assert "Check MSO wrappers" in content
        assert confidence == "HIGH"

    def test_unstructured_response_fallback(self) -> None:
        response = "Just some text without markers."
        content, confidence = SkillUpdateDetector._parse_patch_response(response)
        assert content == "Just some text without markers."
        assert confidence == "MEDIUM"

    def test_invalid_confidence(self) -> None:
        response = "### PATCH_START\nContent\n### PATCH_END\n\n### CONFIDENCE\nMAYBE"
        _, confidence = SkillUpdateDetector._parse_patch_response(response)
        assert confidence == "MEDIUM"


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_identical_content_is_duplicate(self) -> None:
        existing = "Line one.\nLine two.\nLine three."
        assert SkillUpdateDetector._is_duplicate(existing, existing) is True

    def test_new_content_is_not_duplicate(self) -> None:
        existing = "Old content here."
        patch = "Completely new guidance about MSO wrappers."
        assert SkillUpdateDetector._is_duplicate(patch, existing) is False

    def test_empty_patch_is_duplicate(self) -> None:
        assert SkillUpdateDetector._is_duplicate("", "anything") is True

    def test_heading_only_patch_not_counted(self) -> None:
        # Headings are excluded from duplicate check
        patch = "# Just a heading\n## Another heading"
        existing = "# Just a heading\n## Another heading\nSome content."
        assert SkillUpdateDetector._is_duplicate(patch, existing) is True
