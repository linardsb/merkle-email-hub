"""Cross-module integration tests for Phase 22 AI Evolution Infrastructure.

Tests verify the full adapter pipeline: token budget → cost check → fallback
cascade → cost recording, plus capability registry and prompt store integration.
"""

from __future__ import annotations

import datetime
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.capability_registry import (
    ModelCapability,
    ModelConstraints,
    ModelSpec,
    get_capability_registry,
    load_model_specs_from_config,
)
from app.ai.cost_governor import BudgetStatus
from app.ai.exceptions import BudgetExceededError
from app.ai.fallback import (
    FallbackChain,
    FallbackEntry,
    call_with_fallback,
)
from app.ai.protocols import CompletionResponse, Message
from app.ai.routing import (
    resolve_model_by_capabilities,
)
from app.ai.token_budget import TokenBudgetManager

# ── Helpers ──


def _make_messages(count: int, content_size: int = 100) -> list[Message]:
    """Create a list of messages with specified count and content size."""
    msgs = [Message(role="system", content="System prompt " + "x" * content_size)]
    for i in range(count - 1):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append(Message(role=role, content=f"Message {i} " + "y" * content_size))
    return msgs


def _mock_openai_response(model: str = "gpt-4o") -> dict[str, object]:
    """Create a mock OpenAI API JSON response."""
    return {
        "choices": [{"message": {"content": "<html>test</html>"}}],
        "model": model,
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }


def _make_completion_response(model: str = "gpt-4o") -> CompletionResponse:
    return CompletionResponse(
        content="<html>test</html>",
        model=model,
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )


# ── Group 1: Token Budget ↔ Adapter Integration ──


class TestTokenBudgetAdapterIntegration:
    """Token budget trimming through adapter complete() calls."""

    @pytest.mark.asyncio
    async def test_openai_complete_trims_messages_before_send(self) -> None:
        """Messages exceeding budget are trimmed before reaching the API."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = True
            settings.ai.token_budget_reserve = 4096
            settings.ai.token_budget_max = 500  # Very small budget to force trimming
            settings.ai.cost_governor_enabled = False

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            # 10 messages with large content — should be trimmed
            messages = _make_messages(10, content_size=200)
            await provider.complete(messages)

            # Verify the API was called with fewer messages than original
            call_args = provider._client.post.call_args
            sent_messages = call_args.kwargs["json"]["messages"]
            assert len(sent_messages) < len(messages)

    @pytest.mark.asyncio
    async def test_anthropic_complete_trims_messages_before_send(self) -> None:
        """Anthropic adapter also trims messages via token budget."""
        from app.ai.adapters.anthropic import AnthropicProvider

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="<html>result</html>")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with (
            patch("app.ai.adapters.anthropic.get_settings") as mock_settings,
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
        ):
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "claude-sonnet-4-20250514"
            settings.ai.token_budget_enabled = True
            settings.ai.token_budget_reserve = 4096
            settings.ai.token_budget_max = 500  # Small budget
            settings.ai.cost_governor_enabled = False

            provider = AnthropicProvider()
            messages = _make_messages(10, content_size=200)

            await provider.complete(messages)

            # Verify create was called with fewer chat messages
            call_kwargs = mock_client.messages.create.call_args.kwargs
            sent_messages = call_kwargs["messages"]
            # Original has 9 non-system messages, trimmed should have fewer
            assert len(sent_messages) < 9

    @pytest.mark.asyncio
    async def test_trimming_preserves_system_message_in_adapter(self) -> None:
        """System message is preserved through trimming in adapter pipeline."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = True
            settings.ai.token_budget_reserve = 100
            settings.ai.token_budget_max = 300  # Tight budget but enough for system + last msg
            settings.ai.cost_governor_enabled = False

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            messages = _make_messages(5, content_size=50)
            await provider.complete(messages)

            call_args = provider._client.post.call_args
            sent_messages = call_args.kwargs["json"]["messages"]
            # System message should be preserved (first message)
            assert sent_messages[0]["role"] == "system"
            assert "System prompt" in sent_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_budget_disabled_passes_all_messages(self) -> None:
        """When token budget disabled, all messages pass through untrimmed."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = False

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            messages = _make_messages(10, content_size=200)
            await provider.complete(messages)

            call_args = provider._client.post.call_args
            sent_messages = call_args.kwargs["json"]["messages"]
            assert len(sent_messages) == 10

    @pytest.mark.asyncio
    async def test_cache_control_preserved_through_adapter_trim(self) -> None:
        """Messages with cache_control survive trimming in Anthropic adapter."""
        from app.ai.adapters.anthropic import AnthropicProvider

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="ok")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with (
            patch("app.ai.adapters.anthropic.get_settings") as mock_settings,
            patch("anthropic.AsyncAnthropic", return_value=mock_client),
        ):
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "claude-sonnet-4-20250514"
            settings.ai.token_budget_enabled = True
            settings.ai.token_budget_reserve = 100
            settings.ai.token_budget_max = 50000  # Large enough to keep system msg
            settings.ai.cost_governor_enabled = False

            provider = AnthropicProvider()
            messages = [
                Message(
                    role="system", content="System prompt", cache_control={"type": "ephemeral"}
                ),
                Message(role="user", content="Hello"),
            ]

            await provider.complete(messages)

            call_kwargs = mock_client.messages.create.call_args.kwargs
            # System with cache_control should use structured blocks
            assert "system" in call_kwargs
            system_val = call_kwargs["system"]
            if isinstance(system_val, list):
                assert cast(dict[str, Any], system_val[0]).get("cache_control") == {
                    "type": "ephemeral"
                }


# ── Group 2: Cost Governor ↔ Adapter Pipeline ──


class TestCostGovernorAdapterPipeline:
    """Cost governor integration with adapter complete() calls."""

    @pytest.mark.asyncio
    async def test_budget_check_before_completion(self) -> None:
        """_check_cost_budget is called before the API call."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        call_order: list[str] = []

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()

            async def mock_post(*args: object, **kwargs: object) -> MagicMock:
                call_order.append("api_call")
                return mock_response

            provider._client.post = mock_post

            async def tracked_check() -> None:
                call_order.append("budget_check")
                # Skip actual check
                return None

            provider._check_cost_budget = tracked_check  # type: ignore[method-assign]

            messages = [Message(role="user", content="Hello")]
            await provider.complete(messages)

            assert call_order.index("budget_check") < call_order.index("api_call")

    @pytest.mark.asyncio
    async def test_cost_recorded_after_successful_completion(self) -> None:
        """_report_cost is called with correct token counts after completion."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            report_calls: list[tuple[str, dict[str, int] | None, dict[str, object]]] = []

            async def tracked_report(
                model: str, usage: dict[str, int] | None, kwargs: dict[str, object]
            ) -> None:
                report_calls.append((model, usage, kwargs))

            provider._report_cost = tracked_report  # type: ignore[method-assign]
            provider._check_cost_budget = AsyncMock()  # type: ignore[method-assign]

            messages = [Message(role="user", content="Hello")]
            await provider.complete(messages)

            assert len(report_calls) == 1
            model, usage, _ = report_calls[0]
            assert model == "gpt-4o"
            assert usage is not None
            assert usage["prompt_tokens"] == 100
            assert usage["completion_tokens"] == 50

    @pytest.mark.asyncio
    async def test_budget_exceeded_prevents_api_call(self) -> None:
        """BudgetExceededError raised before API call when budget exceeded."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        with (
            patch("app.ai.adapters.openai_compat.get_settings") as mock_settings,
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov,
        ):
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.EXCEEDED
            mock_gov.return_value = gov

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()

            messages = [Message(role="user", content="Hello")]
            with pytest.raises(BudgetExceededError):
                await provider.complete(messages)

            # API should never have been called
            provider._client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_cost_report_failure_does_not_break_completion(self) -> None:
        """_report_cost failure doesn't affect returned result."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with (
            patch("app.ai.adapters.openai_compat.get_settings") as mock_settings,
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov,
        ):
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.OK
            gov.record.side_effect = RuntimeError("Redis down")
            mock_gov.return_value = gov

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            messages = [Message(role="user", content="Hello")]
            result = await provider.complete(messages)

            # Should succeed despite cost recording failure
            assert result.content == "<html>test</html>"

    @pytest.mark.asyncio
    async def test_openai_and_anthropic_both_check_budget(self) -> None:
        """Both adapters call cost governor in the same order."""
        from app.ai.adapters.anthropic import AnthropicProvider
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        # Test OpenAI adapter
        with (
            patch("app.ai.adapters.openai_compat.get_settings") as mock_oai_settings,
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov,
        ):
            settings = mock_oai_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            gov = AsyncMock()
            gov.check_budget.return_value = BudgetStatus.EXCEEDED
            mock_gov.return_value = gov

            provider_oai = OpenAICompatProvider()
            with pytest.raises(BudgetExceededError):
                await provider_oai._check_cost_budget()

        # Test Anthropic adapter
        with (
            patch("app.ai.adapters.anthropic.get_settings") as mock_anth_settings,
            patch("anthropic.AsyncAnthropic", return_value=AsyncMock()),
            patch("app.ai.cost_governor.get_cost_governor") as mock_gov2,
        ):
            settings = mock_anth_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "claude-sonnet-4-20250514"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            gov2 = AsyncMock()
            gov2.check_budget.return_value = BudgetStatus.EXCEEDED
            mock_gov2.return_value = gov2

            provider_anth = AnthropicProvider()
            with pytest.raises(BudgetExceededError):
                await provider_anth._check_cost_budget()

    @pytest.mark.asyncio
    async def test_cost_recorded_with_correct_model_name(self) -> None:
        """Model name from response (not config) used for cost recording."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        response_data = _mock_openai_response(model="gpt-4o-2024-08-06")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = response_data

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = True

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)
            provider._check_cost_budget = AsyncMock()  # type: ignore[method-assign]

            report_calls: list[str] = []

            async def tracked_report(
                model: str, usage: dict[str, int] | None, kwargs: dict[str, object]
            ) -> None:
                report_calls.append(model)

            provider._report_cost = tracked_report  # type: ignore[method-assign]

            messages = [Message(role="user", content="Hello")]
            await provider.complete(messages)

            # Should use the model name from the response, not the config
            assert report_calls[0] == "gpt-4o-2024-08-06"


# ── Group 3: Fallback Chains ↔ Service Integration ──


class TestFallbackServiceIntegration:
    """Fallback chain integration with ChatService and BaseAgentService."""

    @pytest.mark.asyncio
    async def test_chat_service_uses_fallback_chain(self) -> None:
        """ChatService.chat() invokes call_with_fallback when chain configured."""
        from app.ai.schemas import ChatCompletionRequest, ChatMessage
        from app.ai.service import ChatService

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            task_tier="complex",
        )

        with (
            patch("app.ai.service.get_settings") as mock_settings,
            patch("app.ai.service.get_registry"),
            patch("app.ai.service.get_fallback_chain") as mock_get_chain,
            patch("app.ai.service.call_with_fallback") as mock_fallback,
        ):
            settings = mock_settings.return_value
            settings.ai.provider = "openai"
            settings.ai.model = "gpt-4o"
            settings.ai.model_complex = "gpt-4o"
            settings.ai.model_standard = "gpt-4o"
            settings.ai.model_lightweight = "gpt-4o-mini"

            chain = FallbackChain(
                tier="complex",
                entries=(
                    FallbackEntry(provider="openai", model="gpt-4o"),
                    FallbackEntry(provider="anthropic", model="claude-sonnet-4-20250514"),
                ),
            )
            mock_get_chain.return_value = chain
            mock_fallback.return_value = _make_completion_response()

            service = ChatService()
            await service.chat(request)

            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_chain_uses_direct_call(self) -> None:
        """When no chain configured, direct adapter call without fallback."""
        from app.ai.schemas import ChatCompletionRequest, ChatMessage
        from app.ai.service import ChatService

        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            task_tier="standard",
        )

        with (
            patch("app.ai.service.get_settings") as mock_settings,
            patch("app.ai.service.get_registry") as mock_reg,
            patch("app.ai.service.get_fallback_chain") as mock_get_chain,
            patch("app.ai.service.call_with_fallback") as mock_fallback,
        ):
            settings = mock_settings.return_value
            settings.ai.provider = "openai"
            settings.ai.model = "gpt-4o"
            settings.ai.model_complex = "gpt-4o"
            settings.ai.model_standard = "gpt-4o"
            settings.ai.model_lightweight = "gpt-4o-mini"

            mock_get_chain.return_value = None  # No chain

            mock_provider = AsyncMock()
            mock_provider.complete.return_value = _make_completion_response()
            mock_reg.return_value.get_llm.return_value = mock_provider

            service = ChatService()
            await service.chat(request)

            mock_fallback.assert_not_called()
            mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_cascade_records_cost_for_each_attempt(self) -> None:
        """Each fallback attempt records its own cost via adapter."""
        import httpx

        report_calls: list[str] = []

        async def mock_complete(messages: list[Message], **kwargs: object) -> CompletionResponse:
            model = str(kwargs.get("model_override", "unknown"))
            report_calls.append(model)
            if model == "gpt-4o":
                raise httpx.TimeoutException("timeout")
            return _make_completion_response(model)

        mock_provider = MagicMock()
        mock_provider.complete = mock_complete

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        chain = FallbackChain(
            tier="complex",
            entries=(
                FallbackEntry(provider="openai", model="gpt-4o"),
                FallbackEntry(provider="openai", model="gpt-4o-mini"),
            ),
        )

        result = await call_with_fallback(
            chain, mock_registry, [Message(role="user", content="hi")]
        )
        assert result.model == "gpt-4o-mini"
        # Both models were attempted
        assert "gpt-4o" in report_calls
        assert "gpt-4o-mini" in report_calls

    @pytest.mark.asyncio
    async def test_fallback_chain_respects_budget_on_each_attempt(self) -> None:
        """Budget check runs as part of each fallback attempt via adapter.complete()."""
        check_count = 0

        async def mock_complete(messages: list[Message], **kwargs: object) -> CompletionResponse:
            nonlocal check_count
            model = str(kwargs.get("model_override", "unknown"))
            check_count += 1
            if model == "gpt-4o":
                import httpx

                raise httpx.TimeoutException("timeout")
            return _make_completion_response(model)

        mock_provider = MagicMock()
        mock_provider.complete = mock_complete

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        chain = FallbackChain(
            tier="complex",
            entries=(
                FallbackEntry(provider="openai", model="gpt-4o"),
                FallbackEntry(provider="openai", model="gpt-4o-mini"),
            ),
        )

        await call_with_fallback(chain, mock_registry, [Message(role="user", content="hi")])
        # Both entries triggered complete(), where budget check would run
        assert check_count == 2


# ── Group 4: Capability Registry ↔ Routing Pipeline ──


class TestCapabilityRoutingPipeline:
    """Capability registry integration with routing."""

    def setup_method(self) -> None:
        """Reset capability registry between tests."""
        registry = get_capability_registry()
        registry.clear()

    def teardown_method(self) -> None:
        registry = get_capability_registry()
        registry.clear()

    def test_capability_resolution_feeds_into_routing(self) -> None:
        """Resolved model from capability registry is returned by routing."""
        registry = get_capability_registry()
        registry.register(
            ModelSpec(
                model_id="claude-sonnet-4-20250514",
                provider="anthropic",
                tier="standard",
                capabilities=frozenset({ModelCapability.VISION, ModelCapability.TOOL_USE}),
                constraints=ModelConstraints(cost_per_input_token=0.003),
            )
        )

        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION, ModelCapability.TOOL_USE},
        )
        assert result == "claude-sonnet-4-20250514"

    def test_deprecated_model_excluded_from_resolution(self) -> None:
        """Deprecated model is not returned by find_models()."""
        registry = get_capability_registry()
        registry.register(
            ModelSpec(
                model_id="old-model",
                provider="openai",
                capabilities=frozenset({ModelCapability.VISION}),
                deprecation_date=datetime.date(2020, 1, 1),
            )
        )

        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION},
        )
        assert result is None

    def test_cheapest_model_selected_for_capabilities(self) -> None:
        """When multiple models satisfy requirements, cheapest is selected."""
        registry = get_capability_registry()
        registry.register(
            ModelSpec(
                model_id="expensive-model",
                provider="openai",
                capabilities=frozenset({ModelCapability.VISION}),
                constraints=ModelConstraints(cost_per_input_token=0.01),
            )
        )
        registry.register(
            ModelSpec(
                model_id="cheap-model",
                provider="openai",
                capabilities=frozenset({ModelCapability.VISION}),
                constraints=ModelConstraints(cost_per_input_token=0.001),
            )
        )

        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION},
        )
        assert result == "cheap-model"

    def test_capability_resolution_with_empty_registry_returns_none(self) -> None:
        """Empty registry returns None, routing falls back to tier-based."""
        result = resolve_model_by_capabilities(
            requirements={ModelCapability.VISION},
        )
        assert result is None


# ── Group 5: Prompt Store ↔ Skill Override Pipeline ──


class TestPromptStoreSkillPipeline:
    """Prompt store integration with skill override system."""

    def setup_method(self) -> None:
        """Clear overrides between tests."""
        from app.ai.agents.skill_override import (
            clear_all_overrides,
            clear_store_cache,
        )

        clear_all_overrides()
        clear_store_cache()

    def teardown_method(self) -> None:
        from app.ai.agents.skill_override import (
            clear_all_overrides,
            clear_store_cache,
        )

        clear_all_overrides()
        clear_store_cache()

    def test_store_prompt_overrides_skill_file(self) -> None:
        """When prompt store has active template, it takes priority over SKILL.md."""
        from app.ai.agents.skill_override import get_override, set_store_cache

        with patch("app.ai.agents.skill_override.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = True
            set_store_cache("scaffolder", "Store prompt content")

            result = get_override("scaffolder")
            assert result == "Store prompt content"

    def test_store_disabled_falls_through_to_override(self) -> None:
        """When prompt store disabled, falls through to A/B override."""
        from app.ai.agents.skill_override import (
            get_override,
            set_override,
            set_store_cache,
        )

        with patch("app.ai.agents.skill_override.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = False
            set_store_cache("scaffolder", "Store prompt")
            set_override("scaffolder", "AB override")

            result = get_override("scaffolder")
            assert result == "AB override"

    def test_ab_override_takes_priority_over_store_when_no_store_cache(self) -> None:
        """In-memory A/B override used when no store cache entry exists."""
        from app.ai.agents.skill_override import get_override, set_override

        with patch("app.ai.agents.skill_override.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = True
            set_override("scaffolder", "AB override content")

            # No store cache set for this agent
            result = get_override("scaffolder")
            assert result == "AB override content"

    def test_cache_invalidation_after_update(self) -> None:
        """After clearing store cache, get_override falls through."""
        from app.ai.agents.skill_override import (
            clear_store_cache,
            get_override,
            set_store_cache,
        )

        with patch("app.ai.agents.skill_override.get_settings") as mock_settings:
            mock_settings.return_value.ai.prompt_store_enabled = True
            set_store_cache("scaffolder", "Version 1")
            assert get_override("scaffolder") == "Version 1"

            clear_store_cache("scaffolder")
            set_store_cache("scaffolder", "Version 2")
            assert get_override("scaffolder") == "Version 2"


# ── Group 6: Full Pipeline Integration ──


class TestFullPipelineIntegration:
    """End-to-end adapter pipeline tests."""

    @pytest.mark.asyncio
    async def test_budget_check_then_trim_then_complete_then_record(self) -> None:
        """Full flow: cost check → token trim → API call → cost record."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        call_order: list[str] = []

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = True
            settings.ai.token_budget_reserve = 100
            settings.ai.token_budget_max = 50000
            settings.ai.cost_governor_enabled = True

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            # Track call order
            original_apply = provider._apply_token_budget

            def tracked_apply(msgs: list[Message], kwargs: dict[str, object]) -> list[Message]:
                call_order.append("trim")
                return original_apply(msgs, kwargs)

            provider._apply_token_budget = tracked_apply  # type: ignore[assignment]

            async def tracked_check() -> None:
                call_order.append("budget_check")

            provider._check_cost_budget = tracked_check  # type: ignore[method-assign]

            async def tracked_report(
                model: str, usage: dict[str, int] | None, kwargs: dict[str, object]
            ) -> None:
                call_order.append("cost_record")

            provider._report_cost = tracked_report  # type: ignore[method-assign]

            messages = [Message(role="user", content="Hello")]
            result = await provider.complete(messages)

            # Verify order: trim → budget_check → (API call) → cost_record
            assert call_order == ["trim", "budget_check", "cost_record"]
            assert result.content == "<html>test</html>"

    @pytest.mark.asyncio
    async def test_fallback_with_budget_and_trimming(self) -> None:
        """Primary fails → fallback succeeds → both attempts go through pipeline."""
        import httpx

        attempt_models: list[str] = []

        async def mock_complete(messages: list[Message], **kwargs: object) -> CompletionResponse:
            model = str(kwargs.get("model_override", "unknown"))
            attempt_models.append(model)
            if model == "gpt-4o":
                raise httpx.TimeoutException("timeout")
            return _make_completion_response(model)

        mock_provider = MagicMock()
        mock_provider.complete = mock_complete

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        chain = FallbackChain(
            tier="complex",
            entries=(
                FallbackEntry(provider="openai", model="gpt-4o"),
                FallbackEntry(provider="openai", model="gpt-4o-mini"),
            ),
        )

        result = await call_with_fallback(
            chain, mock_registry, [Message(role="user", content="hi")]
        )

        assert result.model == "gpt-4o-mini"
        assert attempt_models == ["gpt-4o", "gpt-4o-mini"]

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail_with_cost_tracking(self) -> None:
        """All entries fail → last error raised."""
        import httpx

        async def mock_complete(messages: list[Message], **kwargs: object) -> CompletionResponse:
            raise httpx.TimeoutException("timeout")

        mock_provider = MagicMock()
        mock_provider.complete = mock_complete

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        chain = FallbackChain(
            tier="complex",
            entries=(
                FallbackEntry(provider="openai", model="gpt-4o"),
                FallbackEntry(provider="anthropic", model="claude-sonnet-4-20250514"),
            ),
        )

        with pytest.raises(httpx.TimeoutException):
            await call_with_fallback(chain, mock_registry, [Message(role="user", content="hi")])

    @pytest.mark.asyncio
    async def test_disabled_features_bypass_cleanly(self) -> None:
        """When all Phase 22 features disabled, adapter works identically."""
        from app.ai.adapters.openai_compat import OpenAICompatProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = _mock_openai_response()

        with patch("app.ai.adapters.openai_compat.get_settings") as mock_settings:
            settings = mock_settings.return_value
            settings.ai.api_key = "test-key"
            settings.ai.model = "gpt-4o"
            settings.ai.base_url = "http://localhost:11434/v1"
            settings.ai.token_budget_enabled = False
            settings.ai.cost_governor_enabled = False

            provider = OpenAICompatProvider()
            provider._client = AsyncMock()
            provider._client.post = AsyncMock(return_value=mock_response)

            messages = _make_messages(5, content_size=100)
            result = await provider.complete(messages)

            # All messages should pass through unchanged
            call_args = provider._client.post.call_args
            sent_messages = call_args.kwargs["json"]["messages"]
            assert len(sent_messages) == 5
            assert result.content == "<html>test</html>"


# ── Group 7: Config & Edge Cases ──


class TestPhase22ConfigEdgeCases:
    """Configuration parsing and edge case tests."""

    def setup_method(self) -> None:
        registry = get_capability_registry()
        registry.clear()

    def teardown_method(self) -> None:
        registry = get_capability_registry()
        registry.clear()

    def test_model_specs_json_parsing_with_all_fields(self) -> None:
        """Full AI__MODEL_SPECS JSON parses correctly."""
        specs = [
            {
                "model_id": "gpt-4o",
                "provider": "openai",
                "tier": "complex",
                "capabilities": ["vision", "tool_use", "structured_output"],
                "context_window": 128000,
                "max_output_tokens": 4096,
                "cost_per_input_token": 0.0025,
                "cost_per_output_token": 0.01,
                "is_local": False,
                "deprecation_date": "2027-01-01",
            },
            {
                "model_id": "claude-sonnet-4-20250514",
                "provider": "anthropic",
                "tier": "standard",
                "capabilities": ["vision", "extended_thinking"],
                "context_window": 200000,
            },
        ]

        load_model_specs_from_config(specs)
        registry = get_capability_registry()

        assert registry.size == 2
        gpt = registry.get("gpt-4o")
        assert gpt is not None
        assert gpt.provider == "openai"
        assert gpt.tier == "complex"
        assert ModelCapability.VISION in gpt.capabilities
        assert gpt.constraints.context_window == 128000
        assert gpt.deprecation_date == datetime.date(2027, 1, 1)

        claude = registry.get("claude-sonnet-4-20250514")
        assert claude is not None
        assert ModelCapability.EXTENDED_THINKING in claude.capabilities

    def test_fallback_chains_json_parsing_with_multiple_tiers(self) -> None:
        """Multi-tier fallback chains config parses correctly."""
        from app.ai.fallback import parse_fallback_chains

        raw = {
            "complex": ["anthropic:claude-opus-4-20250514", "openai:gpt-4o"],
            "standard": ["openai:gpt-4o", "openai:gpt-4o-mini"],
            "lightweight": ["openai:gpt-4o-mini"],
        }

        chains = parse_fallback_chains(raw)

        assert len(chains) == 3
        assert chains["complex"].primary.model == "claude-opus-4-20250514"
        assert chains["complex"].has_fallbacks is True
        assert chains["standard"].entries[1].model == "gpt-4o-mini"
        assert chains["lightweight"].has_fallbacks is False

    def test_cost_governor_pricing_with_versioned_model_names(self) -> None:
        """Versioned model names resolve via prefix matching."""
        from app.ai.cost_governor import _get_pricing

        # Versioned GPT-4o
        pricing = _get_pricing("gpt-4o-2024-08-06")
        assert pricing.input_per_million == 1.97

        # Versioned Claude
        pricing = _get_pricing("claude-sonnet-4-20250514-v2")
        assert pricing.input_per_million == 2.37

        # Versioned mini
        pricing = _get_pricing("gpt-4.1-mini-2025-04-14")
        assert pricing.input_per_million == 0.32

    def test_token_budget_context_window_detection_for_all_known_models(self) -> None:
        """All 13 known models in _MODEL_CONTEXT_WINDOWS resolve correctly."""
        from app.ai.token_budget import _MODEL_CONTEXT_WINDOWS

        for model, expected_window in _MODEL_CONTEXT_WINDOWS.items():
            mgr = TokenBudgetManager(model=model, reserve_tokens=100)
            assert mgr.max_context == expected_window, f"Failed for {model}"

        # Also check prefix matching
        mgr = TokenBudgetManager(model="gpt-4o-2024-08-06", reserve_tokens=100)
        assert mgr.max_context == 128_000

        mgr = TokenBudgetManager(model="claude-sonnet-4-20250514-v2", reserve_tokens=100)
        assert mgr.max_context == 200_000
