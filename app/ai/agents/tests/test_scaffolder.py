"""Unit tests for the Scaffolder agent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.scaffolder.prompt import SKILL_FILES, detect_relevant_skills
from app.ai.agents.scaffolder.schemas import ScaffolderRequest
from app.ai.agents.scaffolder.service import ScaffolderService
from app.ai.exceptions import AIExecutionError
from app.ai.protocols import CompletionResponse
from app.ai.shared import extract_html, sanitize_html_xss

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
            "Here is the email:\n\n"
            "```html\n<table><tr><td>Email</td></tr></table>\n```\n\n"
            "Hope this helps!"
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
        html = '<div onclick="alert(1)" onload="evil()">Content</div>'
        result = sanitize_html_xss(html)
        assert "onclick" not in result
        assert "onload" not in result
        assert "Content" in result

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

    def test_preserves_clean_html_attributes(self) -> None:
        html = (
            '<table role="presentation" cellpadding="0" cellspacing="0">'
            "<tr><td>"
            '<a href="https://example.com">Link</a>'
            '<img src="https://placehold.co/600x300" alt="Hero" '
            'width="600" height="300" style="display: block; border: 0;">'
            "</td></tr></table>"
        )
        result = sanitize_html_xss(html)
        # nh3 may add <tbody> per HTML spec — verify attributes are preserved
        assert 'role="presentation"' in result
        assert 'cellpadding="0"' in result
        assert 'href="https://example.com"' in result
        assert 'alt="Hero"' in result
        assert 'style="display: block; border: 0;"' in result

    def test_removes_self_closing_dangerous_tags(self) -> None:
        html = '<p>Before</p><iframe src="evil.com"></iframe><p>After</p>'
        result = sanitize_html_xss(html)
        assert "<iframe" not in result
        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result


# ── ScaffolderService ──


class TestScaffolderService:
    """Tests for the ScaffolderService orchestration."""

    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='```html\n<table role="presentation"><tr><td>Hello</td></tr></table>\n```',
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )
        return provider

    @pytest.fixture()
    def service(self) -> ScaffolderService:
        return ScaffolderService()

    @pytest.mark.asyncio()
    async def test_generate_success(
        self, service: ScaffolderService, mock_provider: AsyncMock
    ) -> None:
        request = ScaffolderRequest(brief="Create a welcome email for new subscribers")

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.generate(request)

        assert '<table role="presentation">' in response.html
        assert response.model == "test:complex-model"
        assert response.qa_results is None
        assert response.qa_passed is None

    @pytest.mark.asyncio()
    async def test_generate_with_qa(
        self, service: ScaffolderService, mock_provider: AsyncMock
    ) -> None:
        request = ScaffolderRequest(
            brief="Create a welcome email for new subscribers",
            run_qa=True,
        )

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.generate(request)

        assert response.qa_results is not None
        assert len(response.qa_results) == 11
        assert response.qa_passed is not None

    @pytest.mark.asyncio()
    async def test_generate_strips_xss(self, service: ScaffolderService) -> None:
        xss_provider = AsyncMock()
        xss_provider.complete.return_value = CompletionResponse(
            content=(
                "```html\n<table><tr><td>"
                '<script>alert("xss")</script>'
                '<a href="javascript:evil()">Click</a>'
                "</td></tr></table>\n```"
            ),
            model="test-model",
            usage=None,
        )

        request = ScaffolderRequest(brief="Create a promo email for Black Friday sale")

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = xss_provider

            response = await service.generate(request)

        assert "<script" not in response.html
        assert "javascript:" not in response.html

    @pytest.mark.asyncio()
    async def test_generate_llm_failure(self, service: ScaffolderService) -> None:
        failing_provider = AsyncMock()
        failing_provider.complete.side_effect = RuntimeError("LLM unavailable")

        request = ScaffolderRequest(brief="Create a newsletter email template")

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = failing_provider

            with pytest.raises(AIExecutionError, match="scaffolder processing failed"):
                await service.generate(request)


# ── MSO-First Generation (task 11.15) ──


class TestMSOFirstGeneration:
    """Tests for MSO-first generation (task 11.15)."""

    def test_mso_skill_always_loaded(self) -> None:
        """MSO reference loads even without MSO keywords in brief."""
        skills = detect_relevant_skills("Create a simple welcome email")
        assert "mso_vml_quick_ref" in skills

    def test_mso_skill_loaded_with_complex_brief(self) -> None:
        """MSO reference loads in complex brief mode."""
        skills = detect_relevant_skills("x" * 2001)
        assert "mso_vml_quick_ref" in skills

    def test_css_email_reference_in_skill_files(self) -> None:
        """css_email_reference is registered in SKILL_FILES."""
        assert "css_email_reference" in SKILL_FILES

    @pytest.fixture()
    def service(self) -> ScaffolderService:
        return ScaffolderService()

    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.complete.return_value = CompletionResponse(
            content='```html\n<table role="presentation"><tr><td>Hello</td></tr></table>\n```',
            model="test-model",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )
        return provider

    @pytest.mark.asyncio()
    async def test_mso_warnings_in_response(
        self, service: ScaffolderService, mock_provider: AsyncMock
    ) -> None:
        """Response includes mso_warnings field."""
        request = ScaffolderRequest(brief="Create a welcome email for new subscribers")

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider

            response = await service.generate(request)

        assert hasattr(response, "mso_warnings")
        assert isinstance(response.mso_warnings, list)

    @pytest.mark.asyncio()
    async def test_mso_warnings_populated_on_bad_html(self) -> None:
        """MSO validation catches unbalanced conditionals."""
        bad_mso_provider = AsyncMock()
        bad_mso_provider.complete.return_value = CompletionResponse(
            content=(
                '```html\n<html xmlns:v="urn:schemas-microsoft-com:vml">'
                "<head></head><body>"
                "<!--[if mso]><table><tr><td>"
                "<p>Missing closer</p>"
                "</body></html>\n```"
            ),
            model="test-model",
            usage=None,
        )

        service = ScaffolderService()
        request = ScaffolderRequest(brief="Create a welcome email for new subscribers")

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="complex-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = bad_mso_provider

            response = await service.generate(request)

        assert len(response.mso_warnings) > 0
        assert any("balanced_pair" in w for w in response.mso_warnings)
