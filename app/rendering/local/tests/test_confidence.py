"""Tests for rendering confidence scoring."""

from __future__ import annotations

from app.rendering.local.confidence import (
    ConfidenceBreakdown,
    RenderingConfidenceScorer,
    _emulator_coverage_score,
    _table_nesting_depth,
    layout_complexity_score,
)
from app.rendering.local.profiles import CLIENT_PROFILES

# Reuse table-based email skeleton from emulator tests
_SIMPLE_EMAIL = (
    "<!DOCTYPE html>"
    '<html xmlns="http://www.w3.org/1999/xhtml">'
    "<head>"
    '<meta charset="utf-8">'
    "</head>"
    "<body>"
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
    '<tr><td align="center">'
    '<table role="presentation" width="600" cellpadding="0" cellspacing="0">'
    '<tr><td style="padding:20px;font-family:Arial,sans-serif;font-size:16px;color:#333333;">'
    "Hello World"
    "</td></tr>"
    "</table>"
    "</td></tr></table>"
    "</body></html>"
)

_COMPLEX_EMAIL = (
    "<!DOCTYPE html>"
    '<html xmlns="http://www.w3.org/1999/xhtml">'
    "<head>"
    '<meta charset="utf-8">'
    "<style>"
    "@media screen and (max-width: 600px) { .col { width: 100% !important; } }"
    "@media screen and (max-width: 480px) { .col { padding: 10px !important; } }"
    "@media screen and (max-width: 400px) { .btn { width: 100% !important; } }"
    "@media screen and (max-width: 320px) { .img { width: 100% !important; } }"
    "@media (prefers-color-scheme: dark) { .dark { background: #000; } }"
    "@media (prefers-color-scheme: dark) { .dark-text { color: #fff; } }"
    "</style>"
    "</head>"
    "<body>"
    "<!--[if mso]>"
    '<table width="600"><tr><td>'
    "<![endif]-->"
    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
    '<tr><td style="display:flex;position:absolute;">'
    '<table role="presentation"><tr><td>'
    '<table role="presentation"><tr><td>'
    '<table role="presentation"><tr><td>'
    '<table role="presentation"><tr><td>'
    '<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml">Click</v:roundrect>'
    "</td></tr></table>"
    "</td></tr></table>"
    "</td></tr></table>"
    "</td></tr></table>"
    "</td></tr></table>"
    "<!--[if mso]>"
    "</td></tr></table>"
    "<![endif]-->"
    "</body></html>"
)


class TestTableNestingDepth:
    def test_simple_email(self) -> None:
        assert _table_nesting_depth(_SIMPLE_EMAIL) == 2

    def test_complex_email(self) -> None:
        assert _table_nesting_depth(_COMPLEX_EMAIL) >= 4

    def test_no_tables(self) -> None:
        assert _table_nesting_depth("<html><body>Hello</body></html>") == 0


class TestLayoutComplexity:
    def test_simple_email_low_complexity(self) -> None:
        score = layout_complexity_score(_SIMPLE_EMAIL)
        assert score < 0.2

    def test_complex_email_high_complexity(self) -> None:
        score = layout_complexity_score(_COMPLEX_EMAIL)
        # flexbox (+0.15) + absolute (+0.1) + VML (+0.1) + nesting>3 (+0.2)
        # + MSO (+0.05) + media queries>5 (+0.1) = 0.7
        assert score >= 0.5

    def test_capped_at_one(self) -> None:
        score = layout_complexity_score(_COMPLEX_EMAIL)
        assert score <= 1.0


class TestEmulatorCoverage:
    def test_gmail_web_coverage(self) -> None:
        profile = CLIENT_PROFILES["gmail_web"]
        score = _emulator_coverage_score(profile)
        # 6 rules / 8 known = 0.75
        assert 0.6 <= score <= 1.0

    def test_no_emulator_baseline(self) -> None:
        profile = CLIENT_PROFILES["apple_mail"]
        score = _emulator_coverage_score(profile)
        assert score == 0.3  # No emulator = baseline


class TestRenderingConfidenceScorer:
    def test_simple_email_gmail_high_confidence(self) -> None:
        scorer = RenderingConfidenceScorer()
        profile = CLIENT_PROFILES["gmail_web"]
        result = scorer.score(_SIMPLE_EMAIL, profile)
        assert result.score > 70  # Simple email, Gmail = good confidence
        assert isinstance(result.breakdown, ConfidenceBreakdown)
        assert len(result.breakdown.known_blind_spots) > 0

    def test_complex_email_outlook_desktop_low_confidence(self) -> None:
        scorer = RenderingConfidenceScorer()
        profile = CLIENT_PROFILES["outlook_desktop"]
        result = scorer.score(_COMPLEX_EMAIL, profile)
        assert result.score < 70
        assert "Word table cell width" in " ".join(result.breakdown.known_blind_spots)

    def test_thunderbird_high_confidence(self) -> None:
        scorer = RenderingConfidenceScorer()
        profile = CLIENT_PROFILES["thunderbird"]
        result = scorer.score(_SIMPLE_EMAIL, profile)
        assert result.score > 75  # Standards-compliant client

    def test_to_dict_serialization(self) -> None:
        scorer = RenderingConfidenceScorer()
        profile = CLIENT_PROFILES["gmail_web"]
        result = scorer.score(_SIMPLE_EMAIL, profile)
        d = result.to_dict()
        assert "score" in d
        assert "breakdown" in d
        assert "recommendations" in d
        assert isinstance(d["breakdown"]["known_blind_spots"], list)

    def test_all_profiles_score_without_error(self) -> None:
        """Every profile in CLIENT_PROFILES can be scored."""
        scorer = RenderingConfidenceScorer()
        for name, profile in CLIENT_PROFILES.items():
            result = scorer.score(_SIMPLE_EMAIL, profile)
            assert 0 <= result.score <= 100, f"Score out of range for {name}"

    def test_recommendations_for_low_confidence(self) -> None:
        scorer = RenderingConfidenceScorer()
        profile = CLIENT_PROFILES["outlook_desktop"]
        result = scorer.score(_COMPLEX_EMAIL, profile)
        assert len(result.recommendations) > 0

    def test_get_seed_known_client(self) -> None:
        scorer = RenderingConfidenceScorer()
        seed = scorer.get_seed("gmail_web")
        assert seed["accuracy"] == 0.80
        assert seed["sample_count"] == 0

    def test_get_seed_unknown_client(self) -> None:
        scorer = RenderingConfidenceScorer()
        seed = scorer.get_seed("nonexistent_client")
        assert seed["accuracy"] == 0.5
