"""Tests for per-agent context budgets (Phase 2) and decaying handoff history (Phase 3)."""

from app.ai.agents.context_budget import (
    AGENT_BUDGETS,
    ContextBudget,
    compact_handoff_history,
    get_budget,
)
from app.ai.blueprints.protocols import AgentHandoff, HandoffStatus


class TestContextBudget:
    def test_default_budget(self) -> None:
        budget = ContextBudget()
        assert budget.total_max == 12000
        assert budget.system_prompt_max == 4000

    def test_scaffolder_has_larger_budget(self) -> None:
        budget = AGENT_BUDGETS["scaffolder"]
        assert budget.total_max == 16000
        assert budget.user_message_max == 6000

    def test_dark_mode_has_smaller_budget(self) -> None:
        budget = AGENT_BUDGETS["dark_mode"]
        assert budget.total_max == 8000

    def test_get_budget_returns_agent_specific(self) -> None:
        assert get_budget("scaffolder").total_max == 16000

    def test_get_budget_fallback_to_default(self) -> None:
        budget = get_budget("nonexistent_agent")
        assert budget.total_max == 12000

    def test_all_nine_agents_have_budgets(self) -> None:
        expected = {
            "scaffolder",
            "dark_mode",
            "content",
            "accessibility",
            "outlook_fixer",
            "personalisation",
            "code_reviewer",
            "knowledge",
            "innovation",
        }
        assert set(AGENT_BUDGETS.keys()) == expected


class TestDecayingHandoffHistory:
    def _make_handoff(self, name: str, conf: float = 0.9) -> AgentHandoff:
        return AgentHandoff(
            status=HandoffStatus.OK,
            agent_name=name,
            artifact=f"<html>{name}</html>",
            decisions=(f"{name} done",),
            confidence=conf,
        )

    def test_empty_history(self) -> None:
        assert compact_handoff_history([]) == []

    def test_economy_compacts_all(self) -> None:
        history = [self._make_handoff("a"), self._make_handoff("b")]
        result = compact_handoff_history(history, economy=True)
        assert all(isinstance(h, AgentHandoff) and h.artifact == "" for h in result)

    def test_normal_preserves_latest(self) -> None:
        history = [self._make_handoff("a"), self._make_handoff("b")]
        result = compact_handoff_history(history)
        assert isinstance(result[-1], AgentHandoff)
        assert result[-1].artifact != ""  # latest preserved
        assert isinstance(result[0], AgentHandoff)
        assert result[0].artifact == ""  # older compacted

    def test_decay_tiers_with_long_history(self) -> None:
        history = [self._make_handoff(f"agent_{i}") for i in range(6)]
        result = compact_handoff_history(history, decay_tiers=True)

        # Older entries (0, 1, 2) should be summary strings
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)
        assert isinstance(result[2], str)

        # Previous 2 (3, 4) should be compact AgentHandoff
        assert isinstance(result[3], AgentHandoff)
        assert result[3].artifact == ""
        assert isinstance(result[4], AgentHandoff)
        assert result[4].artifact == ""

        # Latest (5) should be full AgentHandoff
        assert isinstance(result[5], AgentHandoff)
        assert result[5].artifact != ""

    def test_decay_tiers_not_triggered_for_short_history(self) -> None:
        history = [self._make_handoff("a"), self._make_handoff("b")]
        result = compact_handoff_history(history, decay_tiers=True)
        # Short history — decay_tiers ignored, normal behavior
        assert all(isinstance(h, AgentHandoff) for h in result)

    def test_summary_string_format(self) -> None:
        handoff = self._make_handoff("dark_mode", conf=0.85)
        summary = handoff.summary()
        assert "dark_mode" in summary
        assert "ok" in summary
        assert "0.85" in summary

    def test_summary_without_confidence(self) -> None:
        handoff = AgentHandoff(agent_name="test", status=HandoffStatus.WARNING)
        summary = handoff.summary()
        assert "test" in summary
        assert "warning" in summary
        assert "conf=" not in summary

    def test_decay_exact_threshold_four(self) -> None:
        history = [self._make_handoff(f"agent_{i}") for i in range(4)]
        result = compact_handoff_history(history, decay_tiers=True)
        # 4 entries: 1 summary + 2 compact + 1 full
        assert isinstance(result[0], str)
        assert isinstance(result[1], AgentHandoff)
        assert result[1].artifact == ""
        assert isinstance(result[2], AgentHandoff)
        assert result[2].artifact == ""
        assert isinstance(result[3], AgentHandoff)
        assert result[3].artifact != ""
