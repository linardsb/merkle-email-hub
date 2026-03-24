# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false
"""Tests for EmailClientFontOptimizer (Phase 31.2)."""

from __future__ import annotations

from app.templates.upload.font_optimizer import EmailClientFontOptimizer


class TestOptimizeFontStack:
    def test_outlook_target_adds_fallbacks(self) -> None:
        """Outlook target: Inter, sans-serif → Inter, Arial, Helvetica, sans-serif."""
        opt = EmailClientFontOptimizer()
        result = opt.optimize_font_stack("Inter, sans-serif", ["outlook_2019_win"])
        assert "Arial" in result
        assert "Helvetica" in result
        # Original font preserved
        assert result.startswith("Inter")

    def test_apple_mail_no_change(self) -> None:
        """Apple Mail supports all fonts — no change needed."""
        opt = EmailClientFontOptimizer()
        result = opt.optimize_font_stack("Inter, sans-serif", ["apple_mail"])
        assert result == "Inter, sans-serif"

    def test_unknown_font_kept_as_is(self) -> None:
        """Font not in fallback_map is returned unchanged."""
        opt = EmailClientFontOptimizer()
        result = opt.optimize_font_stack("CustomBrandFont, serif", ["outlook_2019_win"])
        assert result == "CustomBrandFont, serif"

    def test_no_duplicate_fallbacks(self) -> None:
        """Existing Arial in stack is not duplicated."""
        opt = EmailClientFontOptimizer()
        result = opt.optimize_font_stack("Inter, Arial, sans-serif", ["outlook_2019_win"])
        assert result.count("Arial") == 1


class TestMsoFontAlt:
    def test_mso_font_alt_for_outlook(self) -> None:
        """Returns system font alt for Outlook targets."""
        opt = EmailClientFontOptimizer()
        alt = opt.get_mso_font_alt("Inter, sans-serif")
        assert alt == "Arial"

    def test_mso_font_alt_unknown_font(self) -> None:
        """No alt for unknown font."""
        opt = EmailClientFontOptimizer()
        alt = opt.get_mso_font_alt("UnknownFont, serif")
        assert alt is None

    def test_inject_mso_font_alt(self) -> None:
        """Injects mso-font-alt into inline styles for Outlook targets."""
        opt = EmailClientFontOptimizer()
        html = '<td style="font-family: Inter, sans-serif; color: red">Hi</td>'
        result = opt.inject_mso_font_alt(html, ["outlook_2019_win"])
        assert "mso-font-alt: Arial" in result

    def test_inject_mso_font_alt_skips_non_outlook(self) -> None:
        """No injection when targets don't require mso-font-alt."""
        opt = EmailClientFontOptimizer()
        html = '<td style="font-family: Inter, sans-serif">Hi</td>'
        result = opt.inject_mso_font_alt(html, ["apple_mail"])
        assert "mso-font-alt" not in result

    def test_inject_mso_font_alt_no_duplicate(self) -> None:
        """Skips injection if mso-font-alt already present."""
        opt = EmailClientFontOptimizer()
        html = '<td style="font-family: Inter, sans-serif; mso-font-alt: Arial">Hi</td>'
        result = opt.inject_mso_font_alt(html, ["outlook_2019_win"])
        assert result.count("mso-font-alt") == 1
