from typing import Any
from unittest.mock import MagicMock, patch

from app.ai.skills.amendment import generate_amendments
from app.ai.skills.schemas import PatternCategory, SkillPattern


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
