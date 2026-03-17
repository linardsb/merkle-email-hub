"""Tests for token budget management."""

from app.ai.protocols import Message
from app.ai.token_budget import (
    _CHARS_PER_TOKEN,
    _DEFAULT_CONTEXT_WINDOW,
    _MESSAGE_OVERHEAD_TOKENS,
    TokenBudgetManager,
)


class TestTokenEstimation:
    """Token estimation tests."""

    def test_estimate_empty_messages(self) -> None:
        mgr = TokenBudgetManager(model="gpt-4o-mini", reserve_tokens=1000)
        est = mgr.estimate_tokens([])
        assert est.total_tokens == 0
        assert est.per_message == ()

    def test_estimate_single_message(self) -> None:
        mgr = TokenBudgetManager(model="gpt-4o-mini", reserve_tokens=1000)
        msgs = [Message(role="user", content="Hello world")]
        est = mgr.estimate_tokens(msgs)
        assert est.total_tokens > 0
        assert len(est.per_message) == 1

    def test_estimate_includes_overhead(self) -> None:
        mgr = TokenBudgetManager(model="unknown-model", reserve_tokens=1000)
        msgs = [Message(role="user", content="")]
        est = mgr.estimate_tokens(msgs)
        # Empty content still has role tokens + overhead
        assert est.total_tokens >= _MESSAGE_OVERHEAD_TOKENS

    def test_approximation_method_for_unknown_model(self) -> None:
        """Unknown models without tiktoken use approximation."""
        mgr = TokenBudgetManager(model="some-local-model", reserve_tokens=1000)
        msgs = [Message(role="user", content="a" * 400)]
        est = mgr.estimate_tokens(msgs)
        # 400 chars / 4 = ~100 tokens + overhead
        expected_content = int(400 / _CHARS_PER_TOKEN)
        assert est.total_tokens >= expected_content

    def test_multiple_messages(self) -> None:
        mgr = TokenBudgetManager(model="gpt-4o-mini", reserve_tokens=1000)
        msgs = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="4"),
            Message(role="user", content="Thanks"),
        ]
        est = mgr.estimate_tokens(msgs)
        assert len(est.per_message) == 4
        assert est.total_tokens == sum(est.per_message)


class TestContextWindowDetection:
    """Context window auto-detection tests."""

    def test_known_model(self) -> None:
        mgr = TokenBudgetManager(model="gpt-4o", reserve_tokens=1000)
        assert mgr.max_context == 128_000

    def test_anthropic_model(self) -> None:
        mgr = TokenBudgetManager(model="claude-opus-4-20250514", reserve_tokens=1000)
        assert mgr.max_context == 200_000

    def test_unknown_model_uses_default(self) -> None:
        mgr = TokenBudgetManager(model="my-custom-model", reserve_tokens=1000)
        assert mgr.max_context == _DEFAULT_CONTEXT_WINDOW

    def test_explicit_max_overrides_auto(self) -> None:
        mgr = TokenBudgetManager(
            model="gpt-4o",
            reserve_tokens=1000,
            max_context_tokens=50_000,
        )
        assert mgr.max_context == 50_000

    def test_budget_is_context_minus_reserve(self) -> None:
        mgr = TokenBudgetManager(
            model="gpt-4o-mini",
            reserve_tokens=4096,
            max_context_tokens=16_000,
        )
        assert mgr.budget == 16_000 - 4096


class TestTrimming:
    """Message trimming tests."""

    def _make_msg(self, role: str, size: int) -> Message:
        """Create a message with content of approximately `size` tokens."""
        return Message(role=role, content="x" * int(size * _CHARS_PER_TOKEN))

    def test_no_trimming_when_under_budget(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=100,
            max_context_tokens=10_000,
        )
        msgs = [
            Message(role="system", content="Be helpful"),
            Message(role="user", content="Hello"),
        ]
        result = mgr.trim_to_budget(msgs)
        assert len(result) == 2

    def test_needs_trimming_true(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=100,
            max_context_tokens=200,
        )
        msgs = [self._make_msg("system", 100), self._make_msg("user", 200)]
        assert mgr.needs_trimming(msgs) is True

    def test_needs_trimming_false(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=100,
            max_context_tokens=10_000,
        )
        msgs = [Message(role="system", content="Hi"), Message(role="user", content="Hello")]
        assert mgr.needs_trimming(msgs) is False

    def test_middle_messages_dropped_oldest_first(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=100,
            max_context_tokens=500,
        )
        msgs = [
            Message(role="system", content="System"),
            Message(role="user", content="old message " * 30),
            Message(role="assistant", content="old reply " * 30),
            Message(role="user", content="recent"),
        ]
        result = mgr.trim_to_budget(msgs)
        # System and last message always preserved
        assert result[0].role == "system"
        assert result[-1].content == "recent"
        assert len(result) <= len(msgs)

    def test_system_message_always_preserved(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=100,
            max_context_tokens=500,
        )
        msgs = [
            Message(role="system", content="Important system prompt"),
            Message(role="user", content="x" * 200),
            Message(role="assistant", content="y" * 200),
            Message(role="user", content="Final question"),
        ]
        result = mgr.trim_to_budget(msgs)
        assert result[0].role == "system"

    def test_empty_messages_returns_empty(self) -> None:
        mgr = TokenBudgetManager(model="unknown-model", reserve_tokens=100, max_context_tokens=1000)
        assert mgr.trim_to_budget([]) == []

    def test_system_truncation_when_too_large(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=10,
            max_context_tokens=100,
        )
        msgs = [
            self._make_msg("system", 200),
            Message(role="user", content="question"),
        ]
        result = mgr.trim_to_budget(msgs)
        # System message should be truncated
        assert len(result[0].content) < len(msgs[0].content)
        assert "[...truncated]" in result[0].content

    def test_cache_control_preserved_on_truncation(self) -> None:
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=10,
            max_context_tokens=100,
        )
        msgs = [
            Message(
                role="system",
                content="x" * 2000,
                cache_control={"type": "ephemeral"},
            ),
            Message(role="user", content="question"),
        ]
        result = mgr.trim_to_budget(msgs)
        assert result[0].cache_control == {"type": "ephemeral"}

    def test_two_message_conversation_truncates_system(self) -> None:
        """When only system + user, truncation targets system."""
        mgr = TokenBudgetManager(
            model="unknown-model",
            reserve_tokens=10,
            max_context_tokens=100,
        )
        msgs = [
            self._make_msg("system", 200),
            Message(role="user", content="q"),
        ]
        result = mgr.trim_to_budget(msgs)
        assert len(result) == 2
        assert result[0].role == "system"
        assert result[1].content == "q"


class TestPrefixModelMatch:
    """Test versioned model name matching."""

    def test_versioned_gpt4o(self) -> None:
        mgr = TokenBudgetManager(model="gpt-4o-2024-08-06", reserve_tokens=100)
        assert mgr.max_context == 128_000

    def test_versioned_claude(self) -> None:
        mgr = TokenBudgetManager(model="claude-3-5-sonnet-20241022-v2", reserve_tokens=100)
        assert mgr.max_context == 200_000
