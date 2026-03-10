"""Tests for ontology query helpers."""

from app.knowledge.ontology.query import (
    _compute_severity,
    _property_id_from_css,
    lookup_support,
    unsupported_css_in_html,
)
from app.knowledge.ontology.registry import load_ontology
from app.knowledge.ontology.types import (
    ClientEngine,
    EmailClient,
    SupportLevel,
)


class TestPropertyIdFromCss:
    """Verify CSS property name to ID conversion."""

    def test_name_and_value(self) -> None:
        assert _property_id_from_css("display", "flex") == "display_flex"

    def test_hyphenated_name(self) -> None:
        assert _property_id_from_css("margin-top", None) == "margin_top"

    def test_hyphenated_value(self) -> None:
        assert _property_id_from_css("display", "inline-block") == "display_inline_block"

    def test_whitespace_stripped(self) -> None:
        assert _property_id_from_css("  display  ", "  flex  ") == "display_flex"

    def test_no_value(self) -> None:
        assert _property_id_from_css("border-radius", None) == "border_radius"


class TestLookupSupport:
    """Verify CSS property support lookup."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()

    def test_unsupported_flex_in_outlook(self) -> None:
        level = lookup_support("display", "flex", "outlook_2019_win")
        assert level == SupportLevel.NONE

    def test_supported_block_in_apple(self) -> None:
        level = lookup_support("display", "block", "apple_mail_macos")
        assert level == SupportLevel.FULL


class TestUnsupportedCssInHtml:
    """Verify HTML scanning for unsupported CSS."""

    def setup_method(self) -> None:
        load_ontology.cache_clear()

    def test_detects_flex(self) -> None:
        html = '<div style="display:flex">content</div>'
        issues = unsupported_css_in_html(html)
        flex_issues = [i for i in issues if i["property_id"] == "display_flex"]
        assert len(flex_issues) > 0
        count = flex_issues[0]["unsupported_count"]
        assert isinstance(count, int) and count > 0

    def test_detects_flex_with_space(self) -> None:
        html = '<div style="display: flex">content</div>'
        issues = unsupported_css_in_html(html)
        flex_issues = [i for i in issues if i["property_id"] == "display_flex"]
        assert len(flex_issues) > 0

    def test_no_issues_for_table(self) -> None:
        html = "<table><tr><td>content</td></tr></table>"
        issues = unsupported_css_in_html(html)
        # Tables are universally supported — should have no issues
        assert len(issues) == 0

    def test_severity_included(self) -> None:
        html = '<div style="display:flex">content</div>'
        issues = unsupported_css_in_html(html)
        if issues:
            assert issues[0]["severity"] in ("error", "warning", "info")

    def test_fallback_available_flag(self) -> None:
        html = '<div style="display:flex">content</div>'
        issues = unsupported_css_in_html(html)
        flex_issues = [i for i in issues if i["property_id"] == "display_flex"]
        if flex_issues:
            assert isinstance(flex_issues[0]["fallback_available"], bool)


class TestComputeSeverity:
    """Verify severity computation based on market share."""

    def _make_client(self, share: float) -> EmailClient:
        return EmailClient(
            id="test",
            name="Test",
            family="t",
            platform="web",
            engine=ClientEngine.CUSTOM,
            market_share=share,
        )

    def test_error_severity(self) -> None:
        clients = [self._make_client(15.0), self._make_client(10.0)]
        assert _compute_severity(clients) == "error"

    def test_warning_severity(self) -> None:
        clients = [self._make_client(4.0), self._make_client(3.0)]
        assert _compute_severity(clients) == "warning"

    def test_info_severity(self) -> None:
        clients = [self._make_client(1.0), self._make_client(2.0)]
        assert _compute_severity(clients) == "info"

    def test_empty_list(self) -> None:
        assert _compute_severity([]) == "info"
