"""Unit tests for the Outlook Fixer agent with MSO diagnostic validator."""

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agents.outlook_fixer.mso_repair import (
    format_validation_errors,
    repair_mso_issues,
)
from app.ai.agents.outlook_fixer.schemas import (
    OutlookFixerRequest,
    OutlookFixerResponse,
)
from app.ai.agents.outlook_fixer.service import OutlookFixerService
from app.ai.protocols import CompletionResponse
from app.qa_engine.mso_parser import validate_mso_conditionals

# ── Sample HTML fixtures ──

_VALID_MSO_HTML = (
    '<!DOCTYPE html><html lang="en" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:o="urn:schemas-microsoft-com:office:office">'
    "<head><title>Test</title></head><body>"
    "<!--[if mso]>"
    '<table width="600" cellpadding="0" cellspacing="0"><tr><td>'
    '<v:roundrect arcsize="10%" style="width:200px">'
    '<v:fill color="#0078d4"/>'
    '<v:textbox inset="10px,8px,10px,8px"><center>Click</center></v:textbox>'
    "</v:roundrect>"
    "</td></tr></table>"
    "<![endif]-->"
    "</body></html>"
)

_UNBALANCED_HTML = (
    '<!DOCTYPE html><html lang="en">'
    "<head><title>Test</title></head><body>"
    "<!--[if mso]>"
    "<table><tr><td>MSO content</td></tr></table>"
    "<!--[if mso]>"
    "<table><tr><td>More MSO</td></tr></table>"
    "<![endif]-->"
    "</body></html>"
)

_MISSING_NS_HTML = (
    '<!DOCTYPE html><html lang="en">'
    "<head><title>Test</title></head><body>"
    "<!--[if mso]>"
    '<v:rect style="width:100px;height:100px">'
    '<v:fill color="#ff0000"/>'
    "</v:rect>"
    "<![endif]-->"
    "</body></html>"
)


# ── MSO Repair Tests ──


class TestMsoRepair:
    """Tests for deterministic MSO repair functions."""

    def test_repair_missing_closers(self) -> None:
        result = validate_mso_conditionals(_UNBALANCED_HTML)
        assert not result.is_valid
        assert result.opener_count > result.closer_count

        repaired, repairs = repair_mso_issues(_UNBALANCED_HTML, result)
        assert len(repairs) > 0
        assert "closer" in repairs[0].lower()

        post = validate_mso_conditionals(repaired)
        assert post.opener_count == post.closer_count

    def test_repair_missing_namespaces(self) -> None:
        result = validate_mso_conditionals(_MISSING_NS_HTML)
        assert not result.is_valid

        repaired, repairs = repair_mso_issues(_MISSING_NS_HTML, result)
        assert any("xmlns:v" in r for r in repairs)
        assert any("xmlns:o" in r for r in repairs)

        post = validate_mso_conditionals(repaired)
        assert post.has_vml_namespace
        assert post.has_office_namespace

    def test_valid_html_no_repairs(self) -> None:
        result = validate_mso_conditionals(_VALID_MSO_HTML)
        assert result.is_valid

        repaired, repairs = repair_mso_issues(_VALID_MSO_HTML, result)
        assert repaired == _VALID_MSO_HTML
        assert len(repairs) == 0

    def test_format_validation_errors_empty_for_valid(self) -> None:
        result = validate_mso_conditionals(_VALID_MSO_HTML)
        assert format_validation_errors(result) == ""

    def test_format_validation_errors_structured(self) -> None:
        result = validate_mso_conditionals(_UNBALANCED_HTML)
        formatted = format_validation_errors(result)
        assert "Unbalanced MSO Conditionals" in formatted
        assert "ERROR" in formatted


# ── Service Integration Tests ──


class TestOutlookFixerServiceMsoValidation:
    """Tests for MSO validation integration in service pipeline."""

    @pytest.fixture()
    def service(self) -> OutlookFixerService:
        return OutlookFixerService()

    @pytest.fixture()
    def mock_provider(self) -> AsyncMock:
        provider = AsyncMock()
        provider.complete = AsyncMock(
            return_value=CompletionResponse(
                content=f"```html\n{_VALID_MSO_HTML}\n<!-- CONFIDENCE: 0.92 -->\n```",
                model="test-model",
                usage={"input_tokens": 100, "output_tokens": 200},
            )
        )
        return provider

    @pytest.mark.asyncio()
    async def test_valid_mso_no_retry(
        self, service: OutlookFixerService, mock_provider: AsyncMock
    ) -> None:
        """Valid MSO output should not trigger retry."""
        request = OutlookFixerRequest(html=_VALID_MSO_HTML, run_qa=False)

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider
            response = await service.process(request)

        assert isinstance(response, OutlookFixerResponse)
        assert response.mso_validation_warnings == []
        # Only 1 LLM call (no retry)
        assert mock_provider.complete.call_count == 1

    @pytest.mark.asyncio()
    async def test_unbalanced_mso_gets_repaired(
        self, service: OutlookFixerService, mock_provider: AsyncMock
    ) -> None:
        """Unbalanced MSO should be programmatically repaired if possible."""
        # LLM returns HTML with missing closer
        mock_provider.complete = AsyncMock(
            return_value=CompletionResponse(
                content=f"```html\n{_UNBALANCED_HTML}\n<!-- CONFIDENCE: 0.75 -->\n```",
                model="test-model",
                usage={"input_tokens": 100, "output_tokens": 200},
            )
        )

        request = OutlookFixerRequest(html=_VALID_MSO_HTML, run_qa=False)

        with (
            patch("app.ai.agents.base.get_registry") as mock_registry,
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch("app.ai.agents.base.resolve_model", return_value="standard-model"),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.return_value = mock_provider
            response = await service.process(request)

        assert isinstance(response, OutlookFixerResponse)
        # Should have repair warnings
        assert len(response.mso_validation_warnings) > 0


# ── Blueprint Node Tests ──


class TestOutlookFixerNodeMsoValidation:
    """Tests for MSO validation in blueprint node."""

    def test_mso_warnings_in_valid_html(self) -> None:
        """Valid MSO should produce no warnings."""
        result = validate_mso_conditionals(_VALID_MSO_HTML)
        assert result.is_valid

    def test_mso_warnings_in_invalid_html(self) -> None:
        """Invalid MSO should produce warnings for handoff."""
        result = validate_mso_conditionals(_UNBALANCED_HTML)
        assert not result.is_valid
        warnings = tuple(f"MSO: {issue.message}" for issue in result.issues)
        assert len(warnings) > 0
