"""Tests for structured compatibility brief generation."""

from __future__ import annotations

from app.projects.compatibility_brief import generate_compatibility_brief


class TestGenerateCompatibilityBrief:
    """Tests for structured brief generation from ontology."""

    def test_generates_brief_with_valid_clients(self) -> None:
        """Should return structured brief with client profiles and risk matrix."""
        brief = generate_compatibility_brief(["gmail_web", "outlook_2019_win"])
        assert brief is not None
        assert brief.client_count == 2
        assert len(brief.clients) == 2

        # Client IDs should match
        client_ids = {c.id for c in brief.clients}
        assert client_ids == {"gmail_web", "outlook_2019_win"}

        # Each client should have engine info
        for client in brief.clients:
            assert client.engine in {"webkit", "blink", "word", "gecko", "presto", "custom"}
            assert client.unsupported_count == len(client.unsupported_properties)

    def test_returns_none_for_no_valid_clients(self) -> None:
        """Should return None when no client IDs resolve."""
        assert generate_compatibility_brief(["nonexistent_client"]) is None

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None for empty client_ids."""
        assert generate_compatibility_brief([]) is None

    def test_skips_unknown_keeps_valid(self) -> None:
        """Should skip unknown IDs and include valid ones."""
        brief = generate_compatibility_brief(["gmail_web", "not_real"])
        assert brief is not None
        assert brief.client_count == 1
        assert brief.clients[0].id == "gmail_web"

    def test_dark_mode_warning_word_engine(self) -> None:
        """Should flag dark mode warning when Word engine client targeted."""
        brief = generate_compatibility_brief(["outlook_2019_win"])
        assert brief is not None
        assert brief.dark_mode_warning is True

    def test_no_dark_mode_warning_without_word(self) -> None:
        """Should not flag dark mode warning without Word engine clients."""
        brief = generate_compatibility_brief(["gmail_web"])
        assert brief is not None
        assert brief.dark_mode_warning is False

    def test_risk_matrix_filters_single_client_failures(self) -> None:
        """Risk matrix should only include properties failing in 2+ clients."""
        brief = generate_compatibility_brief(["outlook_2019_win", "outlook_2016_win"])
        assert brief is not None
        for entry in brief.risk_matrix:
            assert len(entry.unsupported_in) >= 2

    def test_risk_matrix_sorted_by_count(self) -> None:
        """Risk matrix entries should be sorted by number of failing clients (desc)."""
        brief = generate_compatibility_brief(["gmail_web", "outlook_2019_win", "outlook_2016_win"])
        assert brief is not None
        if len(brief.risk_matrix) >= 2:
            for i in range(len(brief.risk_matrix) - 1):
                assert len(brief.risk_matrix[i].unsupported_in) >= len(
                    brief.risk_matrix[i + 1].unsupported_in
                )

    def test_total_risky_properties_is_union(self) -> None:
        """total_risky_properties should be the union of all unsupported across clients."""
        brief = generate_compatibility_brief(["gmail_web", "outlook_2019_win"])
        assert brief is not None
        all_css: set[str] = set()
        for c in brief.clients:
            all_css.update(p.css for p in c.unsupported_properties)
        assert brief.total_risky_properties == len(all_css)

    def test_client_profile_metadata(self) -> None:
        """Client profiles should include full metadata."""
        brief = generate_compatibility_brief(["gmail_web"])
        assert brief is not None
        client = brief.clients[0]
        assert client.name  # non-empty
        assert client.platform  # non-empty
        assert client.market_share >= 0
