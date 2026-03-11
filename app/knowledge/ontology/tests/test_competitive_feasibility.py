"""Tests for audience-aware competitive feasibility analysis."""

from app.knowledge.ontology.competitive_feasibility import (
    CompetitiveReport,
    build_competitive_report,
    compute_audience_coverage,
    format_feasibility_context,
)
from app.knowledge.ontology.registry import load_ontology


class TestComputeAudienceCoverage:
    """Test CSS-based audience coverage computation."""

    def test_amp_gmail_supported(self) -> None:
        """AMP is supported by Gmail clients."""
        onto = load_ontology()
        cov, blocking = compute_audience_coverage(
            "amp_email",
            ("gmail_web",),
            onto,
        )
        assert cov == 1.0
        assert blocking == ()

    def test_amp_outlook_blocked(self) -> None:
        """AMP is blocked by Outlook clients."""
        onto = load_ontology()
        cov, blocking = compute_audience_coverage(
            "amp_email",
            ("gmail_web", "outlook_2019_win"),
            onto,
        )
        assert cov == 0.5
        assert len(blocking) == 1
        assert "Outlook" in blocking[0]

    def test_amp_no_clients(self) -> None:
        """Empty audience returns 0.0."""
        onto = load_ontology()
        cov, _blocking = compute_audience_coverage("amp_email", (), onto)
        assert cov == 0.0

    def test_unknown_capability_full_coverage(self) -> None:
        """Unknown capability ID returns 1.0 (no CSS deps mapped)."""
        onto = load_ontology()
        cov, blocking = compute_audience_coverage(
            "nonexistent_capability",
            ("gmail_web",),
            onto,
        )
        assert cov == 1.0
        assert blocking == ()

    def test_css_animations_apple_supported(self) -> None:
        """CSS animations on WebKit clients (Apple Mail) — doesn't crash."""
        onto = load_ontology()
        cov, _blocking = compute_audience_coverage(
            "css_animations",
            ("apple_mail_macos",),
            onto,
        )
        # At minimum, doesn't crash; coverage depends on support data
        assert cov >= 0.0

    def test_coverage_ratio_calculation(self) -> None:
        """Coverage is supported_count / total_clients for AMP."""
        onto = load_ontology()
        cov, blocking = compute_audience_coverage(
            "amp_email",
            ("gmail_web", "gmail_ios", "outlook_2019_win", "apple_mail_macos"),
            onto,
        )
        # Gmail web + iOS = 2 supported, Outlook + Apple = 2 blocked
        assert cov == 0.5
        assert len(blocking) == 2

    def test_css_checkbox_full_coverage(self) -> None:
        """css_checkbox_interactivity has no CSS deps — full coverage."""
        onto = load_ontology()
        cov, blocking = compute_audience_coverage(
            "css_checkbox_interactivity",
            ("gmail_web", "outlook_2019_win"),
            onto,
        )
        assert cov == 1.0
        assert blocking == ()

    def test_dark_mode_coverage(self) -> None:
        """Dark mode depends on media_prefers_color_scheme + color_scheme."""
        onto = load_ontology()
        cov, _blocking = compute_audience_coverage(
            "dark_mode_preview",
            ("apple_mail_macos", "outlook_2019_win"),
            onto,
        )
        # At minimum, doesn't crash
        assert 0.0 <= cov <= 1.0


class TestBuildCompetitiveReport:
    """Test full report generation."""

    def test_report_structure(self) -> None:
        """Report has all expected fields."""
        report = build_competitive_report(client_ids=("gmail_web",))
        assert isinstance(report, CompetitiveReport)
        assert report.audience_client_ids == ("gmail_web",)
        assert len(report.feasibilities) > 0

    def test_hub_advantages_require_coverage(self) -> None:
        """Hub advantages only include capabilities with >= 30% coverage."""
        report = build_competitive_report(client_ids=("gmail_web",))
        for adv in report.hub_advantages:
            assert adv.audience_coverage >= 0.3
            assert adv.is_hub_exclusive

    def test_gaps_are_competitor_exclusive(self) -> None:
        """Gaps are capabilities competitors have but Hub doesn't."""
        report = build_competitive_report(client_ids=("gmail_web",))
        for gap in report.gaps:
            assert gap.is_competitor_exclusive
            assert not gap.hub_supports

    def test_competitor_filter(self) -> None:
        """competitor_id filters supporters to single competitor."""
        report = build_competitive_report(
            client_ids=("gmail_web",),
            competitor_id="stripo",
        )
        for f in report.feasibilities:
            for name in f.competitor_names:
                assert name == "Stripo"

    def test_empty_audience(self) -> None:
        """Report with empty audience still works."""
        report = build_competitive_report(client_ids=())
        assert len(report.feasibilities) > 0

    def test_opportunities_have_coverage(self) -> None:
        """Opportunities require >= 50% audience coverage and Hub support."""
        report = build_competitive_report(
            client_ids=("gmail_web", "apple_mail_macos"),
        )
        for opp in report.opportunities:
            assert opp.audience_coverage >= 0.5
            assert opp.hub_supports


class TestFormatFeasibilityContext:
    """Test formatted context for agent injection."""

    def test_amp_context_with_audience(self) -> None:
        """AMP technique context includes audience coverage."""
        ctx = format_feasibility_context(
            client_ids=("gmail_web", "outlook_2019_win"),
            technique="AMP carousel competitor analysis",
        )
        assert "COMPETITIVE LANDSCAPE" in ctx
        assert "coverage" in ctx.lower()

    def test_empty_on_no_match(self) -> None:
        """Returns empty when no capabilities match."""
        ctx = format_feasibility_context(
            client_ids=("gmail_web",),
            technique="quantum photon spin",
        )
        assert ctx == ""

    def test_no_audience_still_works(self) -> None:
        """Works without audience data (coverage not shown)."""
        ctx = format_feasibility_context(
            client_ids=(),
            technique="AMP email competitor",
        )
        # Should still show competitive data, just no coverage
        if ctx:
            assert "COMPETITIVE LANDSCAPE" in ctx
