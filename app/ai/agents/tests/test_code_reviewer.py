"""Unit tests for the Code Reviewer agent actionability framework."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.agents.code_reviewer.actionability import (
    detect_responsible_agent,
    enrich_with_qa_results,
    format_non_actionable_for_retry,
    is_actionable,
    validate_and_enrich_issues,
)
from app.ai.agents.code_reviewer.schemas import (
    CodeReviewIssue,
    CodeReviewRequest,
    CodeReviewResponse,
    ResponsibleAgent,
    ReviewFocus,
)
from app.ai.agents.code_reviewer.service import (
    CodeReviewService,
    _extract_issues,
    _extract_json_from_fence,
)

# ── Fixtures ──


def _make_issue(
    rule: str = "test-rule",
    severity: str = "warning",
    message: str = "Test message",
    suggestion: str | None = "Replace display:flex with table-based layout for Outlook support",
    current_value: str | None = None,
    fix_value: str | None = None,
    affected_clients: list[str] | None = None,
) -> CodeReviewIssue:
    return CodeReviewIssue(
        rule=rule,
        severity=severity,  # pyright: ignore[reportArgumentType]
        message=message,
        suggestion=suggestion,
        current_value=current_value,
        fix_value=fix_value,
        affected_clients=affected_clients,
    )


# ═══════════════════════════════════════════════════════════════════════
# Agent Detection Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDetectResponsibleAgent:
    def test_mso_keywords_route_to_outlook_fixer(self) -> None:
        issue = _make_issue(rule="mso-conditional", message="Missing MSO closing tag")
        assert detect_responsible_agent(issue) == "outlook_fixer"

    def test_vml_keywords_route_to_outlook_fixer(self) -> None:
        issue = _make_issue(rule="vml-issue", message="Invalid v:rect element")
        assert detect_responsible_agent(issue) == "outlook_fixer"

    def test_dark_mode_keywords_route_to_dark_mode(self) -> None:
        issue = _make_issue(
            rule="dark-mode-missing",
            message="No prefers-color-scheme media query found",
        )
        assert detect_responsible_agent(issue) == "dark_mode"

    def test_data_ogsc_routes_to_dark_mode(self) -> None:
        issue = _make_issue(rule="dark-override", message="Missing data-ogsc selectors")
        assert detect_responsible_agent(issue) == "dark_mode"

    def test_accessibility_keywords_route_to_accessibility(self) -> None:
        issue = _make_issue(rule="a11y-alt", message="Image missing alt text")
        assert detect_responsible_agent(issue) == "accessibility"

    def test_wcag_routes_to_accessibility(self) -> None:
        issue = _make_issue(rule="wcag-violation", message="Low contrast ratio fails WCAG AA")
        assert detect_responsible_agent(issue) == "accessibility"

    def test_personalisation_keywords_route_to_personalisation(self) -> None:
        issue = _make_issue(rule="liquid-syntax", message="Unbalanced Liquid {{ tag")
        assert detect_responsible_agent(issue) == "personalisation"

    def test_ampscript_routes_to_personalisation(self) -> None:
        issue = _make_issue(rule="esp-syntax", message="Unclosed %%[ AMPscript block")
        assert detect_responsible_agent(issue) == "personalisation"

    def test_scaffolder_keywords_route_to_scaffolder(self) -> None:
        issue = _make_issue(rule="structure-issue", message="Missing doctype declaration")
        assert detect_responsible_agent(issue) == "scaffolder"

    def test_generic_issue_defaults_to_code_reviewer(self) -> None:
        issue = _make_issue(rule="redundant-style", message="Duplicate inline styles")
        assert detect_responsible_agent(issue) == "code_reviewer"

    def test_suggestion_text_also_checked(self) -> None:
        issue = _make_issue(
            rule="generic",
            message="Style issue",
            suggestion="Add mso-line-height-rule: exactly for Outlook",
        )
        assert detect_responsible_agent(issue) == "outlook_fixer"


# ═══════════════════════════════════════════════════════════════════════
# Actionability Tests
# ═══════════════════════════════════════════════════════════════════════


class TestIsActionable:
    def test_good_suggestion_passes(self) -> None:
        issue = _make_issue(
            suggestion="Replace display:flex with table-based layout for Outlook compatibility"
        )
        assert is_actionable(issue) is True

    def test_vague_consider_fails(self) -> None:
        issue = _make_issue(suggestion="Consider using a different approach")
        assert is_actionable(issue) is False

    def test_vague_you_should_fails(self) -> None:
        issue = _make_issue(suggestion="You should review the layout structure")
        assert is_actionable(issue) is False

    def test_vague_try_fails(self) -> None:
        issue = _make_issue(suggestion="Try removing the unused styles")
        assert is_actionable(issue) is False

    def test_vague_ensure_fails(self) -> None:
        issue = _make_issue(suggestion="Ensure that all images have alt text")
        assert is_actionable(issue) is False

    def test_vague_avoid_fails(self) -> None:
        issue = _make_issue(suggestion="Avoid using display:flex in emails")
        assert is_actionable(issue) is False

    def test_missing_suggestion_fails(self) -> None:
        issue = _make_issue(suggestion=None)
        assert is_actionable(issue) is False

    def test_empty_suggestion_fails(self) -> None:
        issue = _make_issue(suggestion="")
        assert is_actionable(issue) is False

    def test_short_suggestion_fails(self) -> None:
        issue = _make_issue(suggestion="Fix it")
        assert is_actionable(issue) is False

    def test_suggestion_with_code_passes(self) -> None:
        issue = _make_issue(
            suggestion='Add width="600" and height="200" HTML attributes to the img element',
            current_value="<img src='hero.jpg'>",
            fix_value='<img src="hero.jpg" width="600" height="200">',
        )
        assert is_actionable(issue) is True


# ═══════════════════════════════════════════════════════════════════════
# Format Retry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFormatNonActionableForRetry:
    def test_builds_retry_prompt_for_vague_issues(self) -> None:
        issues = [
            _make_issue(
                rule="css-flex",
                suggestion="Consider using tables instead",
            ),
            _make_issue(
                rule="good-rule",
                suggestion="Replace display:flex with a table-based two-column layout",
            ),
        ]
        result = format_non_actionable_for_retry(issues)
        assert "css-flex" in result
        assert "good-rule" not in result
        assert "change X to Y" in result

    def test_returns_empty_string_when_all_actionable(self) -> None:
        issues = [
            _make_issue(suggestion="Replace display:flex with table-based layout for Outlook"),
        ]
        assert format_non_actionable_for_retry(issues) == ""

    def test_includes_json_format_instruction(self) -> None:
        issues = [_make_issue(suggestion="Consider fixing this")]
        result = format_non_actionable_for_retry(issues)
        assert "JSON array" in result
        assert "current_value" in result


# ═══════════════════════════════════════════════════════════════════════
# Validate and Enrich Tests
# ═══════════════════════════════════════════════════════════════════════


class TestValidateAndEnrichIssues:
    def test_tags_responsible_agents(self) -> None:
        issues = [
            _make_issue(rule="mso-gap", message="Missing MSO closing comment"),
            _make_issue(rule="redundant-style", message="Duplicate font-family"),
        ]
        enriched, _ = validate_and_enrich_issues(issues)
        assert enriched[0].responsible_agent == "outlook_fixer"
        assert enriched[1].responsible_agent == "code_reviewer"

    def test_generates_actionability_warnings(self) -> None:
        issues = [
            _make_issue(suggestion=None),
            _make_issue(suggestion="Replace display:flex with table for Outlook support"),
        ]
        _, warnings = validate_and_enrich_issues(issues)
        assert any("[actionability]" in w for w in warnings)
        assert any("50%" in w for w in warnings)

    def test_no_warnings_when_all_actionable(self) -> None:
        issues = [
            _make_issue(suggestion="Replace display:flex with table for Outlook support"),
        ]
        _, warnings = validate_and_enrich_issues(issues)
        assert len(warnings) == 0

    def test_preserves_all_fields(self) -> None:
        issue = _make_issue(
            current_value="display: flex",
            fix_value="<table>",
            affected_clients=["Outlook 2016"],
        )
        enriched, _ = validate_and_enrich_issues([issue])
        assert enriched[0].current_value == "display: flex"
        assert enriched[0].fix_value == "<table>"
        assert enriched[0].affected_clients == ["Outlook 2016"]


# ═══════════════════════════════════════════════════════════════════════
# QA Cross-Check Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEnrichWithQaResults:
    def test_warns_on_missed_qa_failures(self) -> None:
        # "redundant-style" has no CSS keywords, so css_support failure is missed
        issues = [_make_issue(rule="redundant-style", message="Duplicate font-family")]
        qa_result = MagicMock()
        qa_result.check_name = "css_support"
        qa_result.passed = False
        _, warnings = enrich_with_qa_results(issues, [qa_result])
        assert any("qa_cross_check" in w for w in warnings)

    def test_no_warning_when_domain_covered(self) -> None:
        # Rule and message contain "css" keyword matching css_support domain
        issues = [
            _make_issue(
                rule="unsupported-css-flexbox",
                message="display:flex is unsupported in Outlook",
            )
        ]
        qa_result = MagicMock()
        qa_result.check_name = "css_support"
        qa_result.passed = False
        _, warnings = enrich_with_qa_results(issues, [qa_result])
        assert len(warnings) == 0

    def test_no_warning_when_qa_passes(self) -> None:
        issues = [_make_issue(rule="redundant-style")]
        qa_result = MagicMock()
        qa_result.check_name = "css_support"
        qa_result.passed = True
        _, warnings = enrich_with_qa_results(issues, [qa_result])
        assert len(warnings) == 0

    def test_link_validation_coverage(self) -> None:
        """Link-related rule keywords should cover link_validation QA check."""
        issues = [_make_issue(rule="empty-href", message="Link has empty href attribute")]
        qa_result = MagicMock()
        qa_result.check_name = "link_validation"
        qa_result.passed = False
        _, warnings = enrich_with_qa_results(issues, [qa_result])
        assert len(warnings) == 0

    def test_file_size_coverage(self) -> None:
        """File size rule keywords should cover file_size QA check."""
        issues = [
            _make_issue(
                rule="gmail-clipping",
                message="File size exceeds 102KB clipping threshold",
            )
        ]
        qa_result = MagicMock()
        qa_result.check_name = "file_size"
        qa_result.passed = False
        _, warnings = enrich_with_qa_results(issues, [qa_result])
        assert len(warnings) == 0


# ═══════════════════════════════════════════════════════════════════════
# Extract Issues Tests
# ═══════════════════════════════════════════════════════════════════════


class TestExtractIssues:
    def test_parses_new_fields(self) -> None:
        raw = """```json
{
  "issues": [
    {
      "rule": "css-flex",
      "severity": "critical",
      "line_hint": 10,
      "message": "display:flex unsupported",
      "suggestion": "Use tables",
      "current_value": "display: flex",
      "fix_value": "<table>",
      "affected_clients": ["Outlook 2016", "Gmail"]
    }
  ],
  "summary": "1 issue found"
}
```"""
        issues, _summary = _extract_issues(raw)
        assert len(issues) == 1
        assert issues[0].current_value == "display: flex"
        assert issues[0].fix_value == "<table>"
        assert issues[0].affected_clients == ["Outlook 2016", "Gmail"]

    def test_backward_compat_without_new_fields(self) -> None:
        raw = """```json
{
  "issues": [
    {
      "rule": "old-format",
      "severity": "warning",
      "message": "Old style issue",
      "suggestion": "Fix it"
    }
  ],
  "summary": "1 issue"
}
```"""
        issues, _ = _extract_issues(raw)
        assert len(issues) == 1
        assert issues[0].current_value is None
        assert issues[0].fix_value is None
        assert issues[0].affected_clients is None

    def test_handles_malformed_json(self) -> None:
        issues, summary = _extract_issues("not json at all")
        assert len(issues) == 0
        assert summary == "not json at all"

    def test_handles_empty_issues_array(self) -> None:
        raw = '{"issues": [], "summary": "Clean code"}'
        issues, summary = _extract_issues(raw)
        assert len(issues) == 0
        assert summary == "Clean code"


# ═══════════════════════════════════════════════════════════════════════
# JSON Fence Extraction Tests
# ═══════════════════════════════════════════════════════════════════════


class TestExtractJsonFromFence:
    def test_extracts_from_json_fence(self) -> None:
        raw = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        assert _extract_json_from_fence(raw) == '{"key": "value"}'

    def test_extracts_from_plain_fence(self) -> None:
        raw = '```\n{"key": "value"}\n```'
        assert _extract_json_from_fence(raw) == '{"key": "value"}'

    def test_returns_raw_when_no_fence(self) -> None:
        raw = '{"key": "value"}'
        assert _extract_json_from_fence(raw) == '{"key": "value"}'

    def test_prefers_json_fence_over_plain(self) -> None:
        raw = '```json\n{"correct": true}\n```'
        assert '"correct"' in _extract_json_from_fence(raw)


# ═══════════════════════════════════════════════════════════════════════
# Merge Retry Results Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMergeRetryResults:
    def test_improved_issues_replace_originals(self) -> None:
        service = CodeReviewService()
        original = [
            _make_issue(rule="css-flex", suggestion="Consider using tables"),
        ]
        improved = [
            _make_issue(
                rule="css-flex",
                suggestion="Replace display:flex with a two-column table layout",
                current_value="display: flex",
                fix_value="<table><tr><td>",
            ),
        ]
        merged = service._merge_retry_results(original, improved)
        assert merged[0].current_value == "display: flex"

    def test_preserves_actionable_originals(self) -> None:
        service = CodeReviewService()
        original = [
            _make_issue(
                rule="good-rule",
                suggestion="Replace display:flex with table for Outlook support",
            ),
            _make_issue(rule="vague-rule", suggestion="Consider fixing"),
        ]
        improved = [
            _make_issue(
                rule="vague-rule",
                suggestion="Replace padding shorthand with explicit padding-top/right/bottom/left",
            ),
        ]
        merged = service._merge_retry_results(original, improved)
        assert len(merged) == 2
        # Original good rule preserved
        assert "table for Outlook" in (merged[0].suggestion or "")
        # Vague rule replaced
        assert "padding shorthand" in (merged[1].suggestion or "")

    def test_keeps_original_when_improved_still_vague(self) -> None:
        service = CodeReviewService()
        original = [_make_issue(rule="r1", suggestion="Consider fixing")]
        improved = [_make_issue(rule="r1", suggestion="Try again")]
        merged = service._merge_retry_results(original, improved)
        assert merged[0].suggestion == "Consider fixing"


# ═══════════════════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSchemas:
    def test_review_focus_includes_new_values(self) -> None:
        valid_focuses: list[ReviewFocus] = [
            "redundant_code",
            "css_support",
            "nesting",
            "file_size",
            "link_validation",
            "anti_patterns",
            "spam_patterns",
            "all",
        ]
        for focus in valid_focuses:
            req = CodeReviewRequest(html="x" * 50, focus=focus)
            assert req.focus == focus

    def test_responsible_agent_values(self) -> None:
        valid_agents: list[ResponsibleAgent] = [
            "code_reviewer",
            "outlook_fixer",
            "dark_mode",
            "accessibility",
            "personalisation",
            "scaffolder",
        ]
        for agent in valid_agents:
            issue = CodeReviewIssue(
                rule="test",
                severity="info",
                message="test",
                responsible_agent=agent,
            )
            assert issue.responsible_agent == agent

    def test_new_fields_serialize(self) -> None:
        issue = CodeReviewIssue(
            rule="test",
            severity="critical",
            message="Test",
            current_value="display: flex",
            fix_value="<table>",
            affected_clients=["Outlook", "Gmail"],
            responsible_agent="outlook_fixer",
        )
        data = issue.model_dump()
        assert data["current_value"] == "display: flex"
        assert data["affected_clients"] == ["Outlook", "Gmail"]
        assert data["responsible_agent"] == "outlook_fixer"

    def test_enrich_with_qa_default_false(self) -> None:
        req = CodeReviewRequest(html="x" * 50)
        assert req.enrich_with_qa is False

    def test_actionability_warnings_default_empty(self) -> None:
        resp = CodeReviewResponse(
            html="test",
            summary="test",
            model="test",
        )
        assert resp.actionability_warnings == []


# ═══════════════════════════════════════════════════════════════════════
# Progressive Disclosure Tests
# ═══════════════════════════════════════════════════════════════════════


class TestProgressiveDisclosure:
    def test_detect_skills_all_loads_all_registered(self) -> None:
        from app.ai.agents.code_reviewer.prompt import SKILL_FILES, detect_relevant_skills

        skills = detect_relevant_skills("all")
        assert set(skills) == set(SKILL_FILES.keys())
        assert len(skills) == 10

    def test_detect_skills_css_support_loads_three(self) -> None:
        from app.ai.agents.code_reviewer.prompt import detect_relevant_skills

        skills = detect_relevant_skills("css_support")
        assert "css_client_support" in skills
        assert "css_syntax_validation" in skills
        assert "css_support_matrix" in skills
        assert len(skills) == 3

    def test_detect_skills_anti_patterns_loads_three(self) -> None:
        from app.ai.agents.code_reviewer.prompt import detect_relevant_skills

        skills = detect_relevant_skills("anti_patterns")
        assert "anti_patterns" in skills
        assert "spam_patterns" in skills
        assert "quality_checklist" in skills
        assert len(skills) == 3

    def test_detect_skills_link_validation(self) -> None:
        from app.ai.agents.code_reviewer.prompt import detect_relevant_skills

        skills = detect_relevant_skills("link_validation")
        assert "link_validation" in skills

    def test_detect_skills_spam_patterns(self) -> None:
        from app.ai.agents.code_reviewer.prompt import detect_relevant_skills

        skills = detect_relevant_skills("spam_patterns")
        assert "spam_patterns" in skills
        assert "anti_patterns" in skills


# ═══════════════════════════════════════════════════════════════════════
# Service Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestServiceIntegration:
    @pytest.mark.asyncio
    async def test_process_enriches_issues_with_agent_tags(self) -> None:
        """After process(), issues should have responsible_agent set."""
        llm_json = (
            '{"issues": [{"rule": "mso-gap", "severity": "critical", '
            '"message": "Missing MSO closing tag", "suggestion": "Add the missing mso closing comment tag"}], '
            '"summary": "1 issue"}'
        )
        mock_response = MagicMock()
        mock_response.content = f"<!-- CONFIDENCE: 0.85 -->\n```json\n{llm_json}\n```"
        mock_response.usage = None

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response

        mock_registry = MagicMock()
        mock_registry.get_llm.return_value = mock_provider

        with (
            patch("app.ai.agents.base.get_registry", return_value=mock_registry),
            patch("app.ai.agents.base.get_settings") as mock_settings,
            patch(
                "app.ai.agents.code_reviewer.service.get_registry",
                return_value=mock_registry,
            ),
            patch(
                "app.ai.agents.code_reviewer.service.get_settings",
                return_value=mock_settings.return_value,
            ),
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_settings.return_value.ai.model = "test-model"

            service = CodeReviewService()
            request = CodeReviewRequest(html="x" * 100)
            response = await service.process(request)

            # The MSO issue should be tagged as outlook_fixer
            assert len(response.issues) == 1
            assert response.issues[0].responsible_agent == "outlook_fixer"

    @pytest.mark.asyncio
    async def test_retry_non_actionable_returns_none_on_failure(self) -> None:
        """Retry should return None when LLM call fails."""
        service = CodeReviewService()

        with (
            patch("app.ai.agents.code_reviewer.service.get_settings") as mock_settings,
            patch("app.ai.agents.code_reviewer.service.get_registry") as mock_registry,
        ):
            mock_settings.return_value.ai.provider = "test"
            mock_registry.return_value.get_llm.side_effect = Exception("LLM failed")

            result = await service._retry_non_actionable("retry prompt")
            assert result is None

    def test_contextvar_isolation(self) -> None:
        """ContextVar should not leak between calls."""
        from app.ai.agents.code_reviewer.service import (
            _actionability_warnings_var,
            get_actionability_warnings,
        )

        # Default should be empty
        assert get_actionability_warnings() == []

        # Set and verify
        _actionability_warnings_var.set(["test warning"])
        assert get_actionability_warnings() == ["test warning"]

        # Reset
        _actionability_warnings_var.set(None)
        assert get_actionability_warnings() == []
