from app.ai.skills.extractor import (
    detect_accessibility_patterns,
    detect_dark_mode_patterns,
    detect_esp_patterns,
    detect_performance_patterns,
    detect_progressive_enhancement,
    detect_responsive_patterns,
    detect_vml_patterns,
    extract_patterns,
)
from app.ai.skills.schemas import PatternCategory

VML_BUTTON_HTML = """
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml"
  arcsize="10%" strokecolor="#1e3650" fillcolor="#ff6600"
  style="width:200px; height:40px; v-text-anchor:middle;">
<center style="color:#ffffff; font-family:Arial; font-size:16px;">
  Buy Now
</center>
</v:roundrect>
<![endif]-->
"""

DARK_MODE_HTML = """
<style>
@media (prefers-color-scheme: dark) {
  .dark-bg { background-color: #1a1a1a !important; }
}
[data-ogsc] .dark-text { color: #ffffff !important; }
</style>
<meta name="color-scheme" content="light dark">
"""

PROGRESSIVE_HTML = """
<style>
.flex-container { display: flex; }
</style>
<!--[if mso]><table><tr><td><![endif]-->
<div class="flex-container">content</div>
<!--[if mso]></td></tr></table><![endif]-->
"""

RESPONSIVE_HTML = """
<html><body>
<style>
@media (max-width: 600px) { .mobile { width: 100% !important; } }
</style>
<table width="100%" style="max-width:600px"><tr><td>Content</td></tr></table>
</body></html>
"""

ACCESSIBLE_HTML = """
<html lang="en"><body>
<table role="presentation"><tr><td>
  <a href="#" aria-label="Shop now">Shop</a>
  <a href="#" aria-label="Learn more">Learn</a>
</td></tr></table>
<table role="presentation"><tr><td>Footer</td></tr></table>
<table role="presentation"><tr><td>Spacer</td></tr></table>
<table><tr><th scope="col">Header</th></tr></table>
</body></html>
"""


class TestVmlDetector:
    def test_detects_bulletproof_button(self) -> None:
        patterns = detect_vml_patterns(VML_BUTTON_HTML)
        assert len(patterns) >= 1
        names = [p.pattern_name for p in patterns]
        assert "vml_bulletproof_button" in names
        assert patterns[0].confidence >= 0.9
        assert "outlook_fixer" in patterns[0].applicable_agents

    def test_no_vml_returns_empty(self) -> None:
        assert detect_vml_patterns("<html><body>Hello</body></html>") == []


class TestDarkModeDetector:
    def test_detects_all_dark_mode_signals(self) -> None:
        patterns = detect_dark_mode_patterns(DARK_MODE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "dark_mode_media_query" in names
        assert "outlook_dark_mode_selectors" in names
        assert "color_scheme_meta" in names

    def test_category_is_dark_mode(self) -> None:
        patterns = detect_dark_mode_patterns(DARK_MODE_HTML)
        assert all(p.category == PatternCategory.DARK_MODE for p in patterns)


class TestResponsiveDetector:
    def test_detects_breakpoints(self) -> None:
        patterns = detect_responsive_patterns(RESPONSIVE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "responsive_breakpoints" in names

    def test_detects_fluid_width(self) -> None:
        patterns = detect_responsive_patterns(RESPONSIVE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "fluid_width_with_max_constraint" in names

    def test_no_responsive_returns_empty(self) -> None:
        assert detect_responsive_patterns("<html><body>plain</body></html>") == []


class TestAccessibilityDetector:
    def test_detects_role_presentation(self) -> None:
        patterns = detect_accessibility_patterns(ACCESSIBLE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "layout_table_roles" in names

    def test_detects_aria_labels(self) -> None:
        patterns = detect_accessibility_patterns(ACCESSIBLE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "aria_labels_on_links" in names

    def test_detects_lang_attribute(self) -> None:
        patterns = detect_accessibility_patterns(ACCESSIBLE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "html_lang_attribute" in names

    def test_detects_scope_attributes(self) -> None:
        patterns = detect_accessibility_patterns(ACCESSIBLE_HTML)
        names = {p.pattern_name for p in patterns}
        assert "table_scope_attributes" in names


class TestPerformanceDetector:
    def test_detects_hidden_preheader(self) -> None:
        html = '<div style="display:none;max-height:0;overflow:hidden;">preheader text</div>'
        patterns = detect_performance_patterns(html)
        names = {p.pattern_name for p in patterns}
        assert "hidden_preheader" in names

    def test_no_patterns_in_simple_html(self) -> None:
        assert detect_performance_patterns("<p>Hello</p>") == []


class TestProgressiveEnhancement:
    def test_flexbox_with_mso_fallback(self) -> None:
        patterns = detect_progressive_enhancement(PROGRESSIVE_HTML)
        assert len(patterns) >= 1
        assert patterns[0].pattern_name == "progressive_css_with_table_fallback"
        assert "scaffolder" in patterns[0].applicable_agents


class TestEspDetector:
    def test_liquid_tags(self) -> None:
        html = "<div>{% if user.name %}Hello {{ user.name }}{% endif %}</div>"
        patterns = detect_esp_patterns(html)
        assert len(patterns) >= 1
        assert patterns[0].pattern_name == "liquid_control_flow"
        assert "personalisation" in patterns[0].applicable_agents

    def test_ampscript(self) -> None:
        html = "<div>%%[SET @name = 'Test']%%</div>"
        patterns = detect_esp_patterns(html)
        assert len(patterns) >= 1
        assert patterns[0].pattern_name == "ampscript_syntax"

    def test_merge_tags(self) -> None:
        html = "<div>Hello *|FNAME|*, welcome!</div>"
        patterns = detect_esp_patterns(html)
        assert len(patterns) >= 1
        assert patterns[0].pattern_name == "merge_tag_syntax"

    def test_handlebars(self) -> None:
        html = "<div>{{#if user.premium}}Premium{{/if}}</div>"
        patterns = detect_esp_patterns(html)
        assert len(patterns) >= 1
        assert patterns[0].pattern_name == "handlebars_control_flow"


class TestExtractAll:
    def test_combined_html(self) -> None:
        combined = VML_BUTTON_HTML + DARK_MODE_HTML + PROGRESSIVE_HTML
        patterns = extract_patterns(combined, source_template_id="test-001")
        assert len(patterns) >= 5  # VML + 3 dark mode + progressive
        # Sorted by confidence descending
        confidences = [p.confidence for p in patterns]
        assert confidences == sorted(confidences, reverse=True)
        # All have source template ID
        assert all(p.source_template_id == "test-001" for p in patterns)

    def test_empty_html(self) -> None:
        patterns = extract_patterns("<html><body></body></html>")
        assert patterns == []
