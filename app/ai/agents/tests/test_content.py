"""Unit tests for the Content agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.content.prompt import detect_relevant_skills
from app.ai.agents.content.schemas import ContentRequest
from app.ai.agents.content.service import (
    ContentService,
    check_spam_triggers,
    extract_content,
)
from app.ai.agents.skill_loader import parse_skill_meta
from app.ai.agents.tests.conftest import configure_mock_security
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
            configure_mock_security(mock_settings)
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
            configure_mock_security(mock_settings)
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
            configure_mock_security(mock_settings)
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
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "Target tone: casual" in user_msg

    @pytest.mark.asyncio()
    async def test_generate_flags_spam(self, service: ContentService) -> None:
        spam_provider = AsyncMock()
        spam_provider.complete.return_value = CompletionResponse(
            content="```text\nBuy Now — Act!\n```",
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
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = spam_provider

            response = await service.generate(request)

        assert len(response.spam_warnings) > 0
        triggers = [w.trigger for w in response.spam_warnings]
        assert "buy now" in triggers

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
            configure_mock_security(mock_settings)
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
            configure_mock_security(mock_settings)
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
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.generate(request)

        mock_resolve.assert_called_once_with("lightweight")


# ── Length guardrail tests ──


class TestCleanPunctuation:
    """Tests for excessive punctuation cleanup."""

    def test_excessive_exclamation(self) -> None:
        from app.ai.agents.content.length_guardrail import clean_punctuation

        assert clean_punctuation("Buy now!!!") == "Buy now!"

    def test_excessive_question(self) -> None:
        from app.ai.agents.content.length_guardrail import clean_punctuation

        assert clean_punctuation("Ready???") == "Ready?"

    def test_excessive_ellipsis(self) -> None:
        from app.ai.agents.content.length_guardrail import clean_punctuation

        assert clean_punctuation("Wait for it...") == "Wait for it\u2026"

    def test_no_change_for_single(self) -> None:
        from app.ai.agents.content.length_guardrail import clean_punctuation

        assert clean_punctuation("Hello! Ready? Wait\u2026") == "Hello! Ready? Wait\u2026"

    def test_multiple_patterns(self) -> None:
        from app.ai.agents.content.length_guardrail import clean_punctuation

        assert clean_punctuation("Wow!!! Really??? Yes...") == "Wow! Really? Yes\u2026"


class TestValidateLength:
    """Tests for per-operation length validation."""

    def test_subject_line_within_limits(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("Save 20% on your next order", "subject_line")
        assert result.passed is True
        assert result.warnings == ()

    def test_subject_line_too_long(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        long_subject = "A" * 65
        result = validate_length(long_subject, "subject_line")
        assert result.passed is False
        assert any("exceeds max 60" in w for w in result.warnings)

    def test_subject_line_too_short(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("Hi", "subject_line")
        assert result.passed is False
        assert any("below min 10" in w for w in result.warnings)

    def test_cta_too_many_words(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("Get started with your free trial today", "cta")
        assert result.passed is False
        assert any("words exceeds max 5" in w for w in result.warnings)

    def test_cta_within_limits(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("Start free trial", "cta")
        assert result.passed is True

    def test_cta_too_few_words(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("Go", "cta")
        assert result.passed is False
        assert any("below min 2" in w for w in result.warnings)

    def test_shorten_ratio_too_long(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        original = "This is a fairly long paragraph that should be shortened significantly."
        output = original  # 100% — should fail (max 70%)
        result = validate_length(output, "shorten", original)
        assert result.passed is False
        assert any("max allowed 70%" in w for w in result.warnings)

    def test_shorten_ratio_acceptable(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        original = "This is a fairly long paragraph that should be shortened."
        output = "Shorten this paragraph."  # ~40% — within 50-70%
        result = validate_length(output, "shorten", original)
        # This is 40%, which is below min 50%, so it should warn
        assert any("min allowed 50%" in w for w in result.warnings)

    def test_expand_ratio_acceptable(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        # original=100 chars, output=130 chars → 130% (within 120-150%)
        original = "A" * 100
        output = "A" * 130
        result = validate_length(output, "expand", original)
        assert result.passed is True

    def test_expand_ratio_too_large(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        original = "Short."
        output = "Short. " + "x" * 50  # way over 150%
        result = validate_length(output, "expand", original)
        assert result.passed is False
        assert any("max allowed 150%" in w for w in result.warnings)

    def test_unknown_operation_passes(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        result = validate_length("anything", "unknown_op")
        assert result.passed is True

    def test_preheader_within_limits(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        text = "Discover our latest collection of summer essentials — now with free delivery"
        result = validate_length(text, "preheader")
        assert result.passed is True

    def test_preheader_too_long(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_length

        text = "A" * 105
        result = validate_length(text, "preheader")
        assert result.passed is False
        assert any("exceeds max 100" in w for w in result.warnings)


class TestValidateAlternatives:
    """Tests for batch alternative validation."""

    def test_cleans_punctuation_and_validates(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_alternatives

        alts = ["Buy now!!!", "Save big???"]
        cleaned, warnings = validate_alternatives(alts, "subject_line")
        assert cleaned == ["Buy now!", "Save big?"]
        assert all("exceeds" not in w for w in warnings)

    def test_collects_warnings_across_alternatives(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_alternatives

        alts = ["A" * 65, "Short"]  # first too long, second too short
        _cleaned, warnings = validate_alternatives(alts, "subject_line")
        assert len(warnings) >= 2  # exceeds max + below min

    def test_passes_original_text_for_ratio(self) -> None:
        from app.ai.agents.content.length_guardrail import validate_alternatives

        original = "Original text that needs shortening for the email campaign."
        alts = [original]  # 100% — should fail shorten (max 70%)
        _cleaned, warnings = validate_alternatives(alts, "shorten", original)
        assert any("max allowed 70%" in w for w in warnings)


class TestBuildRetryConstraint:
    """Tests for retry constraint generation."""

    def test_returns_none_for_min_violations_only(self) -> None:
        from app.ai.agents.content.length_guardrail import build_retry_constraint

        warnings = ["subject_line: 5 chars below min 10"]
        result = build_retry_constraint("subject_line", warnings)
        assert result is None

    def test_returns_constraint_for_max_violation(self) -> None:
        from app.ai.agents.content.length_guardrail import build_retry_constraint

        warnings = ["subject_line: 75 chars exceeds max 60"]
        result = build_retry_constraint("subject_line", warnings)
        assert result is not None
        assert "60 characters" in result

    def test_returns_constraint_for_word_violation(self) -> None:
        from app.ai.agents.content.length_guardrail import build_retry_constraint

        warnings = ["cta: 7 words exceeds max 5"]
        result = build_retry_constraint("cta", warnings)
        assert result is not None
        assert "5 words" in result

    def test_returns_constraint_for_ratio_violation(self) -> None:
        from app.ai.agents.content.length_guardrail import build_retry_constraint

        warnings = ["expand: output is 180% of original, max allowed 150%"]
        result = build_retry_constraint("expand", warnings)
        assert result is not None
        assert "150%" in result

    def test_returns_none_for_unknown_operation(self) -> None:
        from app.ai.agents.content.length_guardrail import build_retry_constraint

        warnings = ["unknown: something exceeds max 100"]
        result = build_retry_constraint("unknown", warnings)
        assert result is None


# ── Service-level length guardrail integration tests ──


class TestContentServiceLengthGuardrails:
    """Tests for length validation integrated into the service process() flow."""

    @pytest.fixture()
    def service(self) -> ContentService:
        return ContentService()

    @pytest.mark.asyncio()
    async def test_length_warnings_on_too_long_subject(self, service: ContentService) -> None:
        """Subject line >60 chars triggers retry; if retry also fails, warnings appear."""
        long_subject = "A" * 65 + " subject line that is way too long for email"
        provider = AsyncMock()
        # Both initial and retry return too-long subjects
        provider.complete.return_value = CompletionResponse(
            content=f"```text\n{long_subject}\n```",
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        request = ContentRequest(
            operation="subject_line",
            text="Summer patio furniture sale",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
            patch("app.ai.agents.content.service.get_registry") as mock_retry_registry,
            patch("app.ai.agents.content.service.get_settings") as mock_retry_settings,
            patch("app.ai.agents.content.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = provider
            mock_retry_settings.return_value.ai.provider = "test"
            mock_retry_registry.return_value.get_llm.return_value = provider

            response = await service.generate(request)

        # Both attempts returned too-long subjects, so warnings should be present
        assert len(response.length_warnings) > 0
        assert any("exceeds max 60" in w for w in response.length_warnings)
        # LLM was called twice (initial + retry)
        assert provider.complete.call_count == 2

    @pytest.mark.asyncio()
    async def test_successful_retry_clears_warnings(self, service: ContentService) -> None:
        """When retry produces compliant output, no length warnings."""
        provider = AsyncMock()
        # First call: too long (>60 chars)
        provider.complete.side_effect = [
            CompletionResponse(
                content="```text\n" + "A" * 65 + "\n```",
                model="test-model",
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            ),
            # Retry: compliant (under 60 chars)
            CompletionResponse(
                content="```text\nSave Big on Patio Furniture\n```",
                model="test-model",
                usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
            ),
        ]

        request = ContentRequest(
            operation="subject_line",
            text="Summer patio furniture sale",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
            patch("app.ai.agents.content.service.get_registry") as mock_retry_registry,
            patch("app.ai.agents.content.service.get_settings") as mock_retry_settings,
            patch("app.ai.agents.content.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = provider
            mock_retry_settings.return_value.ai.provider = "test"
            mock_retry_registry.return_value.get_llm.return_value = provider

            response = await service.generate(request)

        assert response.content == ["Save Big on Patio Furniture"]
        assert response.length_warnings == []
        assert provider.complete.call_count == 2

    @pytest.mark.asyncio()
    async def test_min_violation_warns_without_retry(self, service: ContentService) -> None:
        """Min violations (too short) produce warnings but don't trigger retry."""
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content="```text\nHi\n```",
            model="test-model",
            usage={"prompt_tokens": 80, "completion_tokens": 10, "total_tokens": 90},
        )

        request = ContentRequest(
            operation="subject_line",
            text="Summer sale",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = provider

            response = await service.generate(request)

        assert any("below min" in w for w in response.length_warnings)
        # Only 1 LLM call — no retry for min violations
        assert provider.complete.call_count == 1

    @pytest.mark.asyncio()
    async def test_punctuation_cleaned_in_response(self, service: ContentService) -> None:
        """Excessive punctuation in LLM output is cleaned in final response."""
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content="```text\nSummer Sale!!! Ready???\n```",
            model="test-model",
            usage={"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
        )

        request = ContentRequest(
            operation="subject_line",
            text="Summer sale announcement",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = provider

            response = await service.generate(request)

        # Punctuation should be cleaned: !!! → !, ??? → ?
        assert response.content == ["Summer Sale! Ready?"]

    @pytest.mark.asyncio()
    async def test_retry_failure_returns_original_with_warnings(
        self, service: ContentService
    ) -> None:
        """When retry LLM call raises an exception, original response returned with warnings."""
        initial_provider = AsyncMock()
        initial_provider.complete.return_value = CompletionResponse(
            content="```text\n" + "A" * 65 + "\n```",
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        retry_provider = AsyncMock()
        retry_provider.complete.side_effect = RuntimeError("LLM timeout")

        request = ContentRequest(
            operation="subject_line",
            text="Summer sale",
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
            patch("app.ai.agents.content.service.get_registry") as mock_retry_registry,
            patch("app.ai.agents.content.service.get_settings") as mock_retry_settings,
            patch("app.ai.agents.content.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            configure_mock_security(mock_settings)
            mock_registry.return_value.get_llm.return_value = initial_provider
            mock_retry_settings.return_value.ai.provider = "test"
            mock_retry_registry.return_value.get_llm.return_value = retry_provider

            response = await service.generate(request)

        # Should return original with warnings (retry failed gracefully)
        assert len(response.length_warnings) > 0
        assert any("exceeds max 60" in w for w in response.length_warnings)


# ── Skill detection: content rendering constraints ──


class TestDetectRelevantSkillsRendering:
    """Tests for content_rendering_constraints skill detection."""

    def test_subject_line_loads_rendering_constraints(self) -> None:
        skills = detect_relevant_skills(operation="subject_line")
        assert "content_rendering_constraints" in skills

    def test_preheader_loads_rendering_constraints(self) -> None:
        skills = detect_relevant_skills(operation="preheader")
        assert "content_rendering_constraints" in skills

    def test_cta_loads_rendering_constraints(self) -> None:
        skills = detect_relevant_skills(operation="cta")
        assert "content_rendering_constraints" in skills

    def test_body_copy_without_audience_skips_rendering(self) -> None:
        skills = detect_relevant_skills(operation="body_copy")
        assert "content_rendering_constraints" not in skills

    def test_body_copy_with_audience_loads_rendering(self) -> None:
        skills = detect_relevant_skills(
            operation="body_copy",
            audience_client_ids=("outlook_365_win", "gmail_web"),
        )
        assert "content_rendering_constraints" in skills

    def test_any_operation_with_audience_loads_rendering(self) -> None:
        skills = detect_relevant_skills(
            operation="rewrite",
            audience_client_ids=("gmail_web",),
        )
        assert "content_rendering_constraints" in skills

    def test_without_audience_non_text_ops_skip_rendering(self) -> None:
        for op in ("rewrite", "shorten", "expand", "tone_adjust"):
            skills = detect_relevant_skills(operation=op)
            assert "content_rendering_constraints" not in skills

    def test_rendering_constraints_not_duplicated(self) -> None:
        skills = detect_relevant_skills(
            operation="subject_line",
            audience_client_ids=("outlook_365_win",),
        )
        assert skills.count("content_rendering_constraints") == 1


# ── Skill file loading ──


class TestRenderingConstraintsSkillFile:
    """Tests for content_rendering_constraints.md loading and parsing."""

    def test_skill_file_loads(self) -> None:
        from app.ai.agents.content.prompt import _load_skill_file

        content = _load_skill_file("content_rendering_constraints.md")
        assert "Preheader Length" in content
        assert "CTA Button" in content

    def test_skill_meta_parsed(self) -> None:
        from app.ai.agents.content.prompt import _load_skill_file

        content = _load_skill_file("content_rendering_constraints.md")
        meta, body = parse_skill_meta(content)
        assert meta.token_cost == 450
        assert meta.priority == 2
        assert "Preheader Length" in body


# ── Service-layer pass-through ──


class TestServicePassesAudienceClientIds:
    """Verify ContentService.detect_relevant_skills threads audience_client_ids."""

    def test_service_passes_audience_to_prompt(self) -> None:
        service = ContentService()
        request = ContentRequest(
            operation="body_copy",
            text="Summer sale copy",
            audience_client_ids=("outlook_365_win", "gmail_web"),
        )
        skills = service.detect_relevant_skills(request)
        assert "content_rendering_constraints" in skills

    def test_service_omits_rendering_without_audience(self) -> None:
        service = ContentService()
        request = ContentRequest(
            operation="body_copy",
            text="Summer sale copy",
        )
        skills = service.detect_relevant_skills(request)
        assert "content_rendering_constraints" not in skills
