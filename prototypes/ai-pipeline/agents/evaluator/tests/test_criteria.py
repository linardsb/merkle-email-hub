"""Tests for criteria YAML loading — per-agent, fallback, missing files."""

from pathlib import Path

import pytest

from app.ai.agents.evaluator.prompt import _load_criteria


class TestLoadCriteria:
    def test_load_scaffolder_criteria(self) -> None:
        """YAML loads 4 criteria with correct fields for scaffolder."""
        criteria = _load_criteria("scaffolder")
        assert len(criteria) == 4
        names = {c["name"] for c in criteria}
        assert "structural_completeness" in names
        assert "table_based_layout" in names
        assert "slot_coverage" in names
        assert "design_token_application" in names
        for c in criteria:
            assert "description" in c
            assert "weight" in c
            assert isinstance(c["weight"], float)

    def test_load_generic_fallback(self) -> None:
        """Unknown agent -> generic.yaml criteria loaded."""
        criteria = _load_criteria("unknown_agent_xyz")
        assert len(criteria) == 4
        names = {c["name"] for c in criteria}
        assert "html_validity" in names
        assert "no_xss" in names

    def test_missing_criteria_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gracefully returns empty list when criteria dir is empty."""
        monkeypatch.setattr(
            "app.ai.agents.evaluator.prompt._CRITERIA_DIR",
            tmp_path,
        )
        # Also override settings to point to non-existent dir
        from unittest.mock import patch

        with patch("app.ai.agents.evaluator.prompt.get_settings") as mock_settings:
            mock_settings.return_value.ai.evaluator.criteria_dir = str(tmp_path / "nonexistent")
            criteria = _load_criteria("scaffolder")

        assert criteria == []
