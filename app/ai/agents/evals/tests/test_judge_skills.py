"""Tests for judge skill file loading and prompt injection (Phase 43.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import app.ai.agents.evals.judges.base as base_mod
from app.ai.agents.evals.judges.base import (
    _SKILLS_TOKEN_BUDGET,
    _load_skill_file_cached,
    _load_skills_manifest_cached,
    build_system_prompt,
    format_skills_section,
    load_judge_skills,
    set_skills_enabled,
)
from app.ai.agents.evals.judges.schemas import JudgeCriteria


@pytest.fixture(autouse=True)
def _reset_skills_state() -> None:
    """Clear caches and re-enable skills between tests."""
    _load_skills_manifest_cached.cache_clear()
    _load_skill_file_cached.cache_clear()
    set_skills_enabled(True)


def _make_manifest(skills_map: dict[str, list[str]]) -> dict[str, Any]:
    return {"name": "test_judge", "skills": skills_map}


def _write_manifest(
    skills_dir: Path,
    agent: str,
    skills_map: dict[str, list[str]],
) -> Path:
    path = skills_dir / f"{agent}_skills.yaml"
    with path.open("w") as f:
        yaml.dump(_make_manifest(skills_map), f, default_flow_style=False, sort_keys=False)
    return path


def _write_skill_file(skills_dir: Path, name: str, content: str) -> Path:
    path = skills_dir / name
    path.write_text(content)
    return path


_TEST_CRITERIA = [
    JudgeCriteria(name="criterion_a", description="Test criterion A"),
    JudgeCriteria(name="criterion_b", description="Test criterion B"),
    JudgeCriteria(name="criterion_c", description="Test criterion C"),
]


class TestFormatSkillsSection:
    def test_with_manifest_and_files(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Skills section includes header and skill content."""
        _write_manifest(tmp_path, "test_agent", {"criterion_a": ["skill_a.md"]})
        _write_skill_file(tmp_path, "skill_a.md", "# MSO Patterns\nValid nesting rules.")
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        result = format_skills_section("test_agent", _TEST_CRITERIA)

        assert "DOMAIN KNOWLEDGE REFERENCE" in result
        assert "criterion_a" in result
        assert "MSO Patterns" in result
        assert "Valid nesting rules" in result

    def test_missing_manifest_returns_empty(self, tmp_path: Any, monkeypatch: Any) -> None:
        """No manifest → empty string."""
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        result = format_skills_section("nonexistent_agent", _TEST_CRITERIA)
        assert result == ""

    def test_disabled_flag_returns_empty(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Skills disabled → empty string even if files exist."""
        _write_manifest(tmp_path, "test_agent", {"criterion_a": ["skill_a.md"]})
        _write_skill_file(tmp_path, "skill_a.md", "# Skill content")
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        set_skills_enabled(False)
        result = format_skills_section("test_agent", _TEST_CRITERIA)
        assert result == ""


class TestSkillTokenBudget:
    def test_total_budget_respected(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Skills section stays within 2000-token budget even with many large skills."""
        skills_map: dict[str, list[str]] = {}
        for i in range(10):
            name = f"skill_{i}.md"
            skills_map[f"criterion_{i}"] = [name]
            _write_skill_file(tmp_path, name, f"# Skill {i}\n" + "x" * 2000)

        criteria = [JudgeCriteria(name=f"criterion_{i}", description=f"C{i}") for i in range(10)]
        _write_manifest(tmp_path, "test_agent", skills_map)
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        result = format_skills_section("test_agent", criteria)
        total_budget = _SKILLS_TOKEN_BUDGET * 4
        assert len(result) <= total_budget + 200  # header overhead

    def test_per_file_budget_truncates(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Individual skill file exceeding 1000 tokens gets truncated."""
        oversized_content = "# Big Skill\n" + "x" * 5000
        _write_manifest(tmp_path, "test_agent", {"criterion_a": ["big.md"]})
        _write_skill_file(tmp_path, "big.md", oversized_content)
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        result = load_judge_skills("test_agent", "criterion_a")
        per_file_budget = 1000 * 4
        assert len(result) <= per_file_budget + 20  # truncation marker overhead
        assert "[truncated]" in result


class TestBuildSystemPromptWithSkills:
    def test_prompt_includes_skills(self, tmp_path: Any, monkeypatch: Any) -> None:
        """build_system_prompt() injects skills between corrections and IMPORTANT."""
        _write_manifest(tmp_path, "scaffolder", {"brief_fidelity": ["test_skill.md"]})
        _write_skill_file(tmp_path, "test_skill.md", "# Test Domain Knowledge\nKey rule here.")
        monkeypatch.setattr(base_mod, "_SKILLS_DIR", tmp_path)

        from app.ai.agents.evals.judges.scaffolder import SCAFFOLDER_CRITERIA

        result = build_system_prompt(SCAFFOLDER_CRITERIA, "scaffolder")

        assert "DOMAIN KNOWLEDGE REFERENCE" in result
        assert "Test Domain Knowledge" in result
        # Skills appear before IMPORTANT
        skills_pos = result.index("DOMAIN KNOWLEDGE REFERENCE")
        important_pos = result.index("IMPORTANT:")
        assert skills_pos < important_pos
