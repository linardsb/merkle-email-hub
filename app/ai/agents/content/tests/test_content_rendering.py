"""Tests for content agent rendering constraint skill detection (Phase 32.8).

Verifies that detect_relevant_skills() correctly triggers the
content_rendering_constraints skill file based on operation type and
audience context.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.agents.content.prompt import detect_relevant_skills

_SKILL_DIR = Path(__file__).resolve().parent.parent / "skills"

# All 8 content operations
_ALL_OPERATIONS = (
    "subject_line",
    "preheader",
    "cta",
    "body_copy",
    "rewrite",
    "shorten",
    "tone_adjust",
    "expand",
)


class TestContentRenderingConstraints:
    """Skill detection for content_rendering_constraints.md."""

    def test_audience_triggers_constraints(self) -> None:
        result = detect_relevant_skills("body_copy", audience_client_ids=("gmail_web",))
        assert "content_rendering_constraints" in result

    def test_subject_line_always_constraints(self) -> None:
        result = detect_relevant_skills("subject_line")
        assert "content_rendering_constraints" in result

    def test_preheader_always_constraints(self) -> None:
        result = detect_relevant_skills("preheader")
        assert "content_rendering_constraints" in result

    def test_cta_always_constraints(self) -> None:
        result = detect_relevant_skills("cta")
        assert "content_rendering_constraints" in result

    def test_body_copy_no_audience_no_constraints(self) -> None:
        result = detect_relevant_skills("body_copy")
        assert "content_rendering_constraints" not in result

    def test_rewrite_no_audience_no_constraints(self) -> None:
        result = detect_relevant_skills("rewrite")
        assert "content_rendering_constraints" not in result


class TestSkillFileParseable:
    """Verify the content_rendering_constraints.md skill file is valid."""

    def test_skill_file_contains_expected_sections(self) -> None:
        skill_path = _SKILL_DIR / "content_rendering_constraints.md"
        assert skill_path.exists(), f"Skill file not found: {skill_path}"
        content = skill_path.read_text()
        for keyword in ("preheader", "subject", "CTA", "character"):
            assert keyword.lower() in content.lower(), (
                f"Expected section keyword '{keyword}' not found in skill file"
            )


class TestBaseSkillsAlwaysLoaded:
    """Every operation must load operation_best_practices and spam_triggers."""

    def test_base_skills_always_loaded(self) -> None:
        for op in _ALL_OPERATIONS:
            result = detect_relevant_skills(op)
            assert "operation_best_practices" in result, (
                f"operation_best_practices missing for '{op}'"
            )
            assert "spam_triggers" in result, f"spam_triggers missing for '{op}'"
