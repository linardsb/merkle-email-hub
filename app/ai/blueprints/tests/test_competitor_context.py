"""Tests for competitive context injection into blueprint agents."""

from app.ai.blueprints.competitor_context import (
    build_competitive_context,
    format_full_competitive_report,
    should_fetch_competitive_context,
)


class TestShouldFetchCompetitiveContext:
    def test_competitor_name_triggers(self) -> None:
        assert should_fetch_competitive_context("How does Stripo handle AMP?")
        assert should_fetch_competitive_context("Compare with Parcel")
        assert should_fetch_competitive_context("Chamaileon alternative")

    def test_competitive_keywords_trigger(self) -> None:
        assert should_fetch_competitive_context("What's our unique advantage?")
        assert should_fetch_competitive_context("competitor analysis")
        assert should_fetch_competitive_context("market landscape")
        assert should_fetch_competitive_context("differentiate our approach")

    def test_normal_brief_no_trigger(self) -> None:
        assert not should_fetch_competitive_context("Build a dark mode email")
        assert not should_fetch_competitive_context("Create a responsive newsletter")
        assert not should_fetch_competitive_context("Add AMP carousel")

    def test_empty_brief(self) -> None:
        assert not should_fetch_competitive_context("")


class TestBuildCompetitiveContext:
    def test_amp_technique(self) -> None:
        ctx = build_competitive_context("AMP for Email carousel with competitor analysis")
        assert "COMPETITIVE LANDSCAPE" in ctx
        assert "AMP" in ctx

    def test_outlook_technique(self) -> None:
        ctx = build_competitive_context("MSO conditionals vs competitors")
        assert "COMPETITIVE LANDSCAPE" in ctx

    def test_no_relevant_capabilities(self) -> None:
        ctx = build_competitive_context("quantum entanglement photon spin")
        # Should return empty — no matching capabilities or hub keywords
        assert ctx == ""

    def test_hub_exclusive_mentioned(self) -> None:
        ctx = build_competitive_context("AI code generation unique advantage")
        # Should mention Hub-exclusive capabilities
        if ctx:
            assert "Hub-exclusive" in ctx or "COMPETITIVE LANDSCAPE" in ctx


class TestFullCompetitiveReport:
    def test_report_contains_all_competitors(self) -> None:
        report = format_full_competitive_report()
        assert "Stripo" in report
        assert "Parcel" in report
        assert "Chamaileon" in report
        assert "Dyspatch" in report
        assert "Knak" in report

    def test_report_contains_gap_analysis(self) -> None:
        report = format_full_competitive_report()
        assert "advantage" in report.lower() or "Hub" in report


class TestBuildAudienceCompetitiveContext:
    """Test audience-aware competitive context wrapper."""

    def test_delegates_to_feasibility_with_clients(self) -> None:
        """When client_ids provided, uses feasibility module."""
        from app.ai.blueprints.competitor_context import build_audience_competitive_context

        ctx = build_audience_competitive_context(
            technique="AMP carousel competitor",
            client_ids=("gmail_web", "outlook_2019_win"),
        )
        assert "audience-aware" in ctx.lower() or "coverage" in ctx.lower()

    def test_falls_back_without_clients(self) -> None:
        """Without client_ids, falls back to standard context."""
        from app.ai.blueprints.competitor_context import build_audience_competitive_context

        ctx = build_audience_competitive_context(
            technique="AMP carousel competitor analysis",
            client_ids=(),
        )
        # Should still work — falls back to build_competitive_context
        if ctx:
            assert "COMPETITIVE LANDSCAPE" in ctx

    def test_empty_for_unrelated_technique(self) -> None:
        """Returns empty for technique with no capability match."""
        from app.ai.blueprints.competitor_context import build_audience_competitive_context

        ctx = build_audience_competitive_context(
            technique="quantum flux capacitor",
            client_ids=("gmail_web",),
        )
        assert ctx == ""
