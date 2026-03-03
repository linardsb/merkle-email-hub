"""Unit tests for the Dark Mode agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.dark_mode.schemas import DarkModeRequest
from app.ai.agents.dark_mode.service import DarkModeService
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import CompletionResponse
from app.ai.shared import extract_html, sanitize_html_xss

# ── Sample HTML fixtures ──

_SAMPLE_HTML = (
    '<!DOCTYPE html><html lang="en"><head>'
    '<meta name="color-scheme" content="light dark">'
    '<meta name="supported-color-schemes" content="light dark">'
    "<style>"
    "@media (prefers-color-scheme: dark) {"
    "  .dark-bg { background-color: #1a1a2e !important; }"
    "  [data-ogsc] .dark-text { color: #e0e0e0 !important; }"
    "  [data-ogsb] .dark-bg { background-color: #1a1a2e !important; }"
    "}"
    "</style>"
    "</head><body>"
    '<table role="presentation"><tr><td class="dark-bg dark-text">Hello</td></tr></table>'
    "</body></html>"
)

_SAMPLE_LLM_RESPONSE = f"```html\n{_SAMPLE_HTML}\n```"


# ── extract_html ──


class TestExtractHtml:
    """Tests for HTML extraction from LLM responses."""

    def test_extracts_from_html_code_block(self) -> None:
        content = "```html\n<table><tr><td>Hello</td></tr></table>\n```"
        assert extract_html(content) == "<table><tr><td>Hello</td></tr></table>"

    def test_extracts_from_uppercase_tag(self) -> None:
        content = "```HTML\n<div>Content</div>\n```"
        assert extract_html(content) == "<div>Content</div>"

    def test_extracts_from_bare_code_block(self) -> None:
        content = "```\n<p>Bare block</p>\n```"
        assert extract_html(content) == "<p>Bare block</p>"

    def test_falls_back_to_raw_content(self) -> None:
        content = "<table><tr><td>No code block</td></tr></table>"
        assert extract_html(content) == content

    def test_extracts_with_surrounding_text(self) -> None:
        content = (
            "Here is the enhanced email:\n\n"
            "```html\n<table><tr><td>Email</td></tr></table>\n```\n\n"
            "I've added dark mode support!"
        )
        assert extract_html(content) == "<table><tr><td>Email</td></tr></table>"

    def test_strips_whitespace(self) -> None:
        content = "```html\n\n  <p>Padded</p>  \n\n```"
        assert extract_html(content) == "<p>Padded</p>"


# ── sanitize_html_xss ──


class TestSanitizeHtmlXss:
    """Tests for XSS sanitization of generated HTML."""

    def test_removes_script_tags(self) -> None:
        html = '<table><script>alert("xss")</script><tr><td>Safe</td></tr></table>'
        result = sanitize_html_xss(html)
        assert "<script" not in result
        assert "alert" not in result
        assert "<td>Safe</td>" in result

    def test_removes_event_handlers(self) -> None:
        html = '<td onclick="alert(1)" onload="evil()">Content</td>'
        result = sanitize_html_xss(html)
        assert "onclick" not in result
        assert "onload" not in result
        assert "Content</td>" in result

    def test_removes_javascript_protocol(self) -> None:
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_html_xss(html)
        assert "javascript:" not in result
        assert "Click</a>" in result

    def test_removes_iframe(self) -> None:
        html = '<table><tr><td><iframe src="evil.com"></iframe></td></tr></table>'
        result = sanitize_html_xss(html)
        assert "<iframe" not in result

    def test_removes_embed_object_form(self) -> None:
        html = '<embed src="x"><object data="y"></object><form action="z"></form>'
        result = sanitize_html_xss(html)
        assert "<embed" not in result
        assert "<object" not in result
        assert "<form" not in result

    def test_removes_data_uris(self) -> None:
        html = '<img src="data:image/svg+xml;base64,PHN2Zz4=" alt="test">'
        result = sanitize_html_xss(html)
        assert "data:" not in result

    def test_preserves_mso_conditionals(self) -> None:
        html = (
            "<!--[if mso]>"
            '<table role="presentation" width="600"><tr><td>'
            "<![endif]-->"
            "<p>Content</p>"
            "<!--[if mso]></td></tr></table><![endif]-->"
        )
        result = sanitize_html_xss(html)
        assert "<!--[if mso]>" in result
        assert "<![endif]-->" in result
        assert "<p>Content</p>" in result

    def test_preserves_dark_mode_css(self) -> None:
        html = (
            "<style>"
            "@media (prefers-color-scheme: dark) {"
            "  .dark-bg { background-color: #1a1a2e !important; }"
            "  [data-ogsc] .dark-text { color: #e0e0e0 !important; }"
            "  [data-ogsb] .dark-bg { background-color: #1a1a2e !important; }"
            "}"
            "</style>"
            '<table role="presentation"><tr><td>Content</td></tr></table>'
        )
        result = sanitize_html_xss(html)
        assert "prefers-color-scheme" in result
        assert "[data-ogsc]" in result
        assert "[data-ogsb]" in result

    def test_preserves_clean_html(self) -> None:
        html = (
            '<table role="presentation" cellpadding="0" cellspacing="0">'
            "<tr><td>"
            '<a href="https://example.com">Link</a>'
            '<img src="https://placehold.co/600x300" alt="Hero" '
            'width="600" height="300" style="display: block; border: 0;">'
            "</td></tr></table>"
        )
        assert sanitize_html_xss(html) == html

    def test_removes_self_closing_dangerous_tags(self) -> None:
        html = '<p>Before</p><iframe src="evil.com" /><p>After</p>'
        result = sanitize_html_xss(html)
        assert "<iframe" not in result
        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result


# ── DarkModeService ──


class TestDarkModeService:
    """Tests for the DarkModeService orchestration."""

    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content=_SAMPLE_LLM_RESPONSE,
            model="test-model",
            usage={"prompt_tokens": 500, "completion_tokens": 800, "total_tokens": 1300},
        )
        return provider

    @pytest.fixture()
    def service(self) -> DarkModeService:
        return DarkModeService()

    @pytest.mark.asyncio()
    async def test_process_success(
        self, service: DarkModeService, mock_provider: AsyncMock
    ) -> None:
        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>"
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.process(request)

        assert "color-scheme" in response.html
        assert "prefers-color-scheme" in response.html
        assert "[data-ogsc]" in response.html
        assert "[data-ogsb]" in response.html
        assert response.model == "test:standard-model"
        assert response.qa_results is None
        assert response.qa_passed is None

    @pytest.mark.asyncio()
    async def test_process_with_qa(
        self, service: DarkModeService, mock_provider: AsyncMock
    ) -> None:
        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>",
            run_qa=True,
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.process(request)

        assert response.qa_results is not None
        assert len(response.qa_results) == 10
        assert response.qa_passed is not None
        # Dark mode check should be first and should pass (our sample has all markers)
        assert response.qa_results[0].check_name == "dark_mode"
        assert response.qa_results[0].passed is True

    @pytest.mark.asyncio()
    async def test_process_with_color_overrides(
        self, service: DarkModeService, mock_provider: AsyncMock
    ) -> None:
        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>",
            color_overrides={"#ffffff": "#121212", "#333333": "#e0e0e0"},
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.process(request)

        # Verify the user message includes colour overrides
        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "#ffffff" in user_msg
        assert "#121212" in user_msg

    @pytest.mark.asyncio()
    async def test_process_with_preserve_colors(
        self, service: DarkModeService, mock_provider: AsyncMock
    ) -> None:
        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>",
            preserve_colors=["#ff6600", "#003366"],
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.process(request)

        # Verify the user message includes preserved colours
        call_args = mock_provider.complete.call_args
        user_msg = call_args[0][0][1].content
        assert "#ff6600" in user_msg
        assert "#003366" in user_msg

    @pytest.mark.asyncio()
    async def test_process_strips_xss(self, service: DarkModeService) -> None:
        xss_provider = AsyncMock()
        xss_provider.complete.return_value = CompletionResponse(
            content=(
                "```html\n<html><body><table><tr><td>"
                '<script>alert("xss")</script>'
                '<a href="javascript:evil()">Click</a>'
                "</td></tr></table></body></html>\n```"
            ),
            model="test-model",
            usage=None,
        )

        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>"
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = xss_provider

            response = await service.process(request)

        assert "<script" not in response.html
        assert "javascript:" not in response.html

    @pytest.mark.asyncio()
    async def test_process_llm_failure(self, service: DarkModeService) -> None:
        failing_provider = AsyncMock()
        failing_provider.complete.side_effect = RuntimeError("LLM unavailable")

        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>"
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch("app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = failing_provider

            with pytest.raises(AIExecutionError, match="Dark mode processing failed"):
                await service.process(request)

    @pytest.mark.asyncio()
    async def test_process_uses_standard_tier(
        self, service: DarkModeService, mock_provider: AsyncMock
    ) -> None:
        request = DarkModeRequest(
            html="<html><body><table><tr><td>Hello World Email</td></tr></table></body></html>"
        )

        with (
            patch("app.ai.agents.dark_mode.service.get_registry") as mock_registry,
            patch("app.ai.agents.dark_mode.service.get_settings") as mock_settings,
            patch(
                "app.ai.agents.dark_mode.service.resolve_model", return_value="standard-model"
            ) as mock_resolve,
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            await service.process(request)

        mock_resolve.assert_called_once_with("standard")
