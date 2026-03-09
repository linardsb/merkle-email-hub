"""Unit tests for the Content agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.content.schemas import ContentRequest
from app.ai.agents.content.service import (
    ContentService,
    check_spam_triggers,
    extract_content,
)
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import CompletionResponse

# ── extract_content ──


class TestExtractContent:
    """Tests for content extraction from LLM responses."""

    def test_extracts_from_text_code_block(self) -> None:
        raw = "```text\nTransform Your Patio: 30% Off\n```"
        assert extract_content(raw) == ["Transform Your Patio: 30% Off"]

    def test_extracts_from_uppercase_tag(self) -> None:
        raw = "```TEXT\nSummer Savings Start Here\n```"
        assert extract_content(raw) == ["Summer Savings Start Here"]

    def test_extracts_from_bare_code_block(self) -> None:
        raw = "```\nBare block content\n```"
        assert extract_content(raw) == ["Bare block content"]

    def test_falls_back_to_raw_content(self) -> None:
        raw = "Just plain text, no code block"
        assert extract_content(raw) == ["Just plain text, no code block"]

    def test_splits_by_delimiter(self) -> None:
        raw = "```text\nFirst alternative\n---\nSecond alternative\n---\nThird alternative\n```"
        result = extract_content(raw)
        assert len(result) == 3
        assert result[0] == "First alternative"
        assert result[1] == "Second alternative"
        assert result[2] == "Third alternative"

    def test_strips_empty_alternatives(self) -> None:
        raw = "```text\nFirst\n---\n\n---\nThird\n```"
        result = extract_content(raw)
        assert len(result) == 2
        assert result[0] == "First"
        assert result[1] == "Third"

    def test_strips_whitespace_from_alternatives(self) -> None:
        raw = "```text\n  Padded text  \n---\n  Another padded  \n```"
        result = extract_content(raw)
        assert result[0] == "Padded text"
        assert result[1] == "Another padded"

    def test_handles_surrounding_text(self) -> None:
        raw = (
            "Here are some subject lines:\n\n"
            "```text\nGreat Subject Line\n---\nAnother Option\n```\n\n"
            "Let me know if you'd like more!"
        )
        result = extract_content(raw)
        assert len(result) == 2
        assert result[0] == "Great Subject Line"


# ── check_spam_triggers ──


class TestCheckSpamTriggers:
    """Tests for spam trigger detection."""

    def test_detects_known_triggers(self) -> None:
        texts = ["Buy Now and Save Big!", "Act Now - Limited Time Offer"]
        warnings = check_spam_triggers(texts)
        triggers = [w.trigger for w in warnings]
        assert "buy now" in triggers
        assert "act now" in triggers
        assert "limited time" in triggers

    def test_returns_empty_for_clean_copy(self) -> None:
        texts = ["Transform your patio this summer", "Discover our new collection"]
        warnings = check_spam_triggers(texts)
        assert warnings == []

    def test_returns_context_snippet(self) -> None:
        texts = ["Don't miss this chance to buy now before stock runs out"]
        warnings = check_spam_triggers(texts)
        assert len(warnings) >= 1
        buy_now_warning = next(w for w in warnings if w.trigger == "buy now")
        assert "buy now" in buy_now_warning.context.lower()

    def test_case_insensitive_matching(self) -> None:
        texts = ["CLICK HERE for details"]
        warnings = check_spam_triggers(texts)
        triggers = [w.trigger for w in warnings]
        assert "click here" in triggers


# ── ContentService ──


class TestContentService:
    """Tests for the ContentService orchestration."""

    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content=(
                "```text\n"
                "Transform Your Patio: 30% Off\n"
                "---\n"
                "Summer Savings Start Here\n"
                "---\n"
                "Your Dream Patio Awaits\n"
                "---\n"
                "Outdoor Living Made Affordable\n"
                "---\n"
                "Refresh Your Space for Less\n"
                "```"
            ),
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        return provider

    @pytest.fixture()
    def service(self) -> ContentService:
        return ContentService()

    @pytest.mark.asyncio()
    async def test_generate_subject_lines(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        request = ContentRequest(
            operation="subject_line",
            text="Summer patio furniture sale, 30% off all items",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.generate(request)

        assert len(response.content) == 5
        assert response.operation == "subject_line"
        assert response.model == "test:standard-model"

    @pytest.mark.asyncio()
    async def test_generate_single_rewrite(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        mock_provider.complete.return_value = CompletionResponse(
            content="```text\nRevamped copy that reads better\n```",
            model="test-model",
            usage={"prompt_tokens": 80, "completion_tokens": 30, "total_tokens": 110},
        )

        request = ContentRequest(
            operation="rewrite",
            text="Original copy that needs improvement",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.generate(request)

        assert len(response.content) == 1
        assert response.content[0] == "Revamped copy that reads better"
        assert response.operation == "rewrite"

    @pytest.mark.asyncio()
    async def test_generate_with_brand_voice(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        request = ContentRequest(
            operation="subject_line",
            text="New product launch",
            brand_voice="Playful, witty, uses puns. Never formal.",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "Playful, witty, uses puns" in user_msg
        assert "Brand voice guidelines" in user_msg

    @pytest.mark.asyncio()
    async def test_generate_with_tone(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        request = ContentRequest(
            operation="tone_adjust",
            text="Please review the attached document at your earliest convenience.",
            tone="casual",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "Target tone: casual" in user_msg

    @pytest.mark.asyncio()
    async def test_generate_flags_spam(self, service: ContentService) -> None:
        spam_provider = AsyncMock()
        spam_provider.complete.return_value = CompletionResponse(
            content="```text\nBuy Now and Save — Act Now!\n```",
            model="test-model",
            usage=None,
        )

        request = ContentRequest(
            operation="cta",
            text="Promote summer sale",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = spam_provider

            response = await service.generate(request)

        assert len(response.spam_warnings) > 0
        triggers = [w.trigger for w in response.spam_warnings]
        assert "buy now" in triggers
        assert "act now" in triggers

    @pytest.mark.asyncio()
    async def test_generate_llm_failure(self, service: ContentService) -> None:
        failing_provider = AsyncMock()
        failing_provider.complete.side_effect = RuntimeError("LLM unavailable")

        request = ContentRequest(
            operation="rewrite",
            text="Some text to rewrite",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = failing_provider

            with pytest.raises(AIExecutionError, match="content processing failed"):
                await service.generate(request)

    @pytest.mark.asyncio()
    async def test_uses_standard_tier(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        request = ContentRequest(
            operation="subject_line",
            text="Summer sale announcement",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch(
                "app.ai.agents.base.resolve_model", return_value="standard-model"
            ) as mock_resolve,
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        mock_resolve.assert_called_once_with("standard")

    @pytest.mark.asyncio()
    async def test_uses_lightweight_tier(
        self, service: ContentService, mock_provider: AsyncMock
    ) -> None:
        mock_provider.complete.return_value = CompletionResponse(
            content="```text\nShortened version of the text\n```",
            model="test-model",
            usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        )

        request = ContentRequest(
            operation="shorten",
            text="Long text that needs to be shortened significantly",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="light-model") as mock_resolve,
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        mock_resolve.assert_called_once_with("lightweight")
