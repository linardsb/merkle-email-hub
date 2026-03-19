from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from app.ai.skills.amendment import apply_amendments, generate_amendments
from app.ai.skills.schemas import PatternCategory, SkillAmendment, SkillPattern


def _make_pattern(**overrides: Any) -> SkillPattern:
    defaults: dict[str, Any] = {
        "pattern_name": "test_pattern",
        "category": PatternCategory.OUTLOOK_FIX,
        "description": "Test description",
        "html_example": "<v:rect>test</v:rect>",
        "confidence": 0.9,
        "applicable_agents": ["outlook_fixer"],
    }
    defaults.update(overrides)
    return SkillPattern(**defaults)


class TestGenerateAmendments:
    @patch("app.ai.skills.amendment.get_settings")
    @patch("app.ai.skills.amendment._is_duplicate", return_value=False)
    def test_generates_amendment_for_high_confidence(
        self, _mock_dup: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.return_value.skill_extraction.min_confidence = 0.7
        pattern = _make_pattern(confidence=0.9)
        amendments = generate_amendments([pattern])
        assert len(amendments) >= 1
        assert amendments[0].agent_name == "outlook_fixer"

    @patch("app.ai.skills.amendment.get_settings")
    def test_skips_low_confidence(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.skill_extraction.min_confidence = 0.7
        pattern = _make_pattern(confidence=0.5)
        amendments = generate_amendments([pattern])
        assert len(amendments) == 0

    @patch("app.ai.skills.amendment.get_settings")
    @patch("app.ai.skills.amendment._is_duplicate", return_value=False)
    def test_multiple_agents(self, _mock_dup: MagicMock, mock_settings: MagicMock) -> None:
        mock_settings.return_value.skill_extraction.min_confidence = 0.7
        pattern = _make_pattern(
            applicable_agents=["outlook_fixer", "scaffolder"],
        )
        amendments = generate_amendments([pattern])
        agents = {a.agent_name for a in amendments}
        assert "outlook_fixer" in agents
        assert "scaffolder" in agents

    @patch("app.ai.skills.amendment.get_settings")
    @patch("app.ai.skills.amendment._is_duplicate", return_value=True)
    def test_skips_duplicates(self, _mock_dup: MagicMock, mock_settings: MagicMock) -> None:
        mock_settings.return_value.skill_extraction.min_confidence = 0.7
        pattern = _make_pattern(confidence=0.9)
        amendments = generate_amendments([pattern])
        assert len(amendments) == 0


class TestApplyAmendments:
    def test_empty_amendments_list(self) -> None:
        """Empty list -> report with all zeros."""
        report = apply_amendments([], dry_run=True)
        assert report.total == 0
        assert report.applied == 0
        assert report.skipped_duplicate == 0

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Skill file path outside app/ai/agents/ -> skipped."""
        amendment = SkillAmendment(
            id="evil",
            agent_name="outlook_fixer",
            skill_file="../../etc/passwd",
            section="## Exploit",
            content="malicious",
            confidence=0.95,
            source_pattern_id="p2",
        )
        report = apply_amendments([amendment], dry_run=True)
        # Path traversal is blocked — amendment doesn't count as applied
        assert report.applied == 0

    def test_dry_run_generates_diffs(self, tmp_path: Path) -> None:
        """dry_run=True produces diffs without writing files."""
        skill_dir = tmp_path / "outlook_fixer" / "skills"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "vml_reference.md"
        skill_file.write_text("# VML Reference\n\nExisting content.\n")

        amendment = SkillAmendment(
            id="test1",
            agent_name="outlook_fixer",
            skill_file="skills/vml_reference.md",
            section="Auto-Extracted Patterns",
            content="New VML pattern",
            confidence=0.9,
            source_pattern_id="p1",
        )
        with patch("app.ai.skills.amendment._SKILL_BASE", tmp_path):
            report = apply_amendments([amendment], dry_run=True)
        assert report.applied == 1
        assert len(report.diffs) == 1
        # File should NOT have been modified in dry-run
        assert "New VML pattern" not in skill_file.read_text()

    def test_apply_writes_file(self, tmp_path: Path) -> None:
        """dry_run=False actually writes to the skill file."""
        skill_dir = tmp_path / "scaffolder" / "skills"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "email_structure.md"
        skill_file.write_text("# Email Structure\n\nContent.\n")

        amendment = SkillAmendment(
            id="test2",
            agent_name="scaffolder",
            skill_file="skills/email_structure.md",
            section="Auto-Extracted Patterns",
            content="Grid fallback pattern",
            confidence=0.85,
            source_pattern_id="p3",
        )
        with patch("app.ai.skills.amendment._SKILL_BASE", tmp_path):
            report = apply_amendments([amendment], dry_run=False)
        assert report.applied == 1
        assert "Grid fallback pattern" in skill_file.read_text()

    def test_duplicate_in_file_skipped(self, tmp_path: Path) -> None:
        """Content with matching pattern_id in file -> skipped_duplicate."""
        skill_dir = tmp_path / "outlook_fixer" / "skills"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "vml_reference.md"
        # File already contains the pattern ID
        skill_file.write_text("# VML\n\nExisting p_existing pattern.\n")

        amendment = SkillAmendment(
            id="dup",
            agent_name="outlook_fixer",
            skill_file="skills/vml_reference.md",
            section="Patterns",
            content="Duplicate content",
            confidence=0.9,
            source_pattern_id="p_existing",
        )
        with patch("app.ai.skills.amendment._SKILL_BASE", tmp_path):
            report = apply_amendments([amendment], dry_run=True)
        assert report.skipped_duplicate == 1
        assert report.applied == 0

    def test_report_diff_format(self, tmp_path: Path) -> None:
        """Diffs contain file path and diff_preview."""
        skill_dir = tmp_path / "dark_mode" / "skills"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "color_remapping.md"
        skill_file.write_text("# Color Remapping\n")

        amendment = SkillAmendment(
            id="fmt",
            agent_name="dark_mode",
            skill_file="skills/color_remapping.md",
            section="Auto-Extracted Patterns",
            content="Dark mode swap",
            confidence=0.88,
            source_pattern_id="p_fmt",
        )
        with patch("app.ai.skills.amendment._SKILL_BASE", tmp_path):
            report = apply_amendments([amendment], dry_run=True)
        assert len(report.diffs) == 1
        assert "file" in report.diffs[0]
        assert "diff_preview" in report.diffs[0]
