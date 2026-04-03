"""Validate all 61 new component HTML files meet quality contracts."""

from __future__ import annotations

import re

import pytest

from app.components.data.file_loader import _REPO_ROOT, load_file_components

_HTML_DIR = _REPO_ROOT / "email-templates" / "components"

NEW_SLUGS: list[str] = [
    # Content: Countdown
    "countdown-timer",
    "countdown-timer-inline",
    "countdown-timer-dark",
    "countdown-timer-banner",
    # Content: Testimonial
    "testimonial",
    "testimonial-card",
    "testimonial-minimal",
    # Content: Pricing
    "pricing-table",
    "pricing-table-highlight",
    "pricing-table-comparison",
    # Content: Team/Bio
    "team-bio",
    "team-bio-horizontal",
    # Content: Event
    "event-card",
    "event-card-minimal",
    "event-card-banner",
    # Content: Video
    "video-placeholder",
    "video-placeholder-overlay",
    "video-placeholder-inline",
    # Content: FAQ
    "faq-item",
    "faq-list",
    # Content: Social Proof
    "social-proof",
    "social-proof-rating",
    "social-proof-logos",
    "social-proof-quote",
    # Content: Zigzag/Layout
    "zigzag-image-left",
    "zigzag-image-right",
    "zigzag-alternating",
    "hero-asymmetric",
    "hero-asymmetric-reverse",
    "mosaic-2x2",
    "mosaic-featured",
    "card-grid-2",
    "card-grid-3",
    "card-grid-4",
    "sidebar-left",
    "sidebar-right",
    # Content: Structural Variants
    "text-block-centered",
    "hero-video",
    "hero-split",
    "hero-minimal",
    # Structure: Navigation
    "nav-multi-level",
    "nav-centered",
    "nav-icon",
    # Structure: Announcement
    "announcement-bar",
    "announcement-bar-dismissible",
    "announcement-bar-countdown",
    # Structure: App Download
    "app-download",
    "app-download-inline",
    # Structure: Loyalty
    "loyalty-points",
    "loyalty-progress",
    # Structure: Footer/Header Variants
    "footer-minimal",
    "footer-centered",
    "header-centered",
    "header-with-nav",
    # Utility: Divider/Spacer Variants
    "divider-fancy",
    "divider-dotted",
    "spacer-responsive",
    # Interactive
    "survey-cta",
    "survey-scale",
    "progressive-disclosure",
    "progressive-disclosure-tabs",
]

# Components that are purely decorative (no data-slots expected)
_NO_SLOT_SLUGS = frozenset(
    {
        "divider-fancy",
        "divider-dotted",
        "spacer-responsive",
    }
)

# Components with multi-column layouts that must have MSO conditionals
_COMPLEX_SLUGS = frozenset(
    {
        "pricing-table-comparison",
        "team-bio-horizontal",
        "video-placeholder-inline",
        "social-proof",
        "social-proof-logos",
        "zigzag-image-left",
        "zigzag-image-right",
        "zigzag-alternating",
        "hero-asymmetric",
        "hero-asymmetric-reverse",
        "hero-split",
        "mosaic-2x2",
        "mosaic-featured",
        "card-grid-2",
        "card-grid-3",
        "card-grid-4",
        "sidebar-left",
        "sidebar-right",
        "nav-icon",
        "survey-cta",
        "header-with-nav",
    }
)

# Catches divs with true layout CSS (float, flex, columns).
# Allows hybrid column pattern (display:inline-block + width) used in email HTML.
_DIV_LAYOUT_RE = re.compile(
    r"<div[^>]*style\s*=\s*\"[^\"]*"
    r"(?:float\s*:|(?<![a-z-])flex(?![a-z-])|columns\s*:)"
    r"[^\"]*\"",
    re.IGNORECASE,
)

_DATA_SLOT_RE = re.compile(r'data-slot="([^"]+)"')


def _read_html(slug: str) -> str:
    path = _HTML_DIR / f"{slug}.html"
    assert path.is_file(), f"Missing HTML file: {path}"
    return path.read_text()


class TestNewComponentStructure:
    """Structural quality checks for all 61 new component HTML files."""

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_html_file_exists(self, slug: str) -> None:
        path = _HTML_DIR / f"{slug}.html"
        assert path.is_file(), f"Missing HTML file: {path}"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_no_div_layout(self, slug: str) -> None:
        """No <div> with layout CSS (width/flex/float/columns)."""
        html = _read_html(slug)
        # Strip MSO conditionals — divs inside <!--[if mso]> blocks are allowed
        cleaned = re.sub(
            r"<!--\[if[^\]]*\]>.*?<!\[endif\]-->",
            "",
            html,
            flags=re.DOTALL,
        )
        matches = _DIV_LAYOUT_RE.findall(cleaned)
        assert not matches, f"{slug}: div with layout CSS found: {matches}"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_tables_have_role_presentation(self, slug: str) -> None:
        """All <table> elements have role='presentation'."""
        html = _read_html(slug)
        # Strip MSO conditionals
        cleaned = re.sub(
            r"<!--\[if[^\]]*\]>.*?<!\[endif\]-->",
            "",
            html,
            flags=re.DOTALL,
        )
        tables = re.findall(r"<table[^>]*>", cleaned, re.IGNORECASE)
        for tag in tables:
            assert 'role="presentation"' in tag, (
                f"{slug}: table missing role='presentation': {tag[:80]}"
            )

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_tables_have_cellpadding_zero(self, slug: str) -> None:
        """All tables have cellpadding=0 cellspacing=0."""
        html = _read_html(slug)
        cleaned = re.sub(
            r"<!--\[if[^\]]*\]>.*?<!\[endif\]-->",
            "",
            html,
            flags=re.DOTALL,
        )
        tables = re.findall(r"<table[^>]*>", cleaned, re.IGNORECASE)
        for tag in tables:
            assert 'cellpadding="0"' in tag, f"{slug}: table missing cellpadding=0: {tag[:80]}"
            assert 'cellspacing="0"' in tag, f"{slug}: table missing cellspacing=0: {tag[:80]}"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_images_have_display_block(self, slug: str) -> None:
        """All <img> have display:block in style (except overlay icons with position:absolute)."""
        html = _read_html(slug)
        imgs = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
        for tag in imgs:
            style_match = re.search(r'style="([^"]*)"', tag)
            if style_match:
                style = style_match.group(1).lower()
                # Overlay icons with position:absolute are exempt from display:block
                if "position" in style and "absolute" in style:
                    continue
                assert "display" in style and "block" in style, (
                    f"{slug}: img missing display:block: {tag[:80]}"
                )

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_images_have_meaningful_alt(self, slug: str) -> None:
        """No generic/empty alt text on images."""
        html = _read_html(slug)
        imgs = re.findall(r"<img[^>]*>", html, re.IGNORECASE)
        for tag in imgs:
            alt_match = re.search(r'alt="([^"]*)"', tag)
            assert alt_match, f"{slug}: img missing alt attribute: {tag[:80]}"
            alt_text = alt_match.group(1).strip().lower()
            assert alt_text not in ("", "image", "img", "photo", "picture"), (
                f"{slug}: img has generic alt text: '{alt_text}'"
            )

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_has_data_slots(self, slug: str) -> None:
        """Components with content have at least 1 data-slot attr."""
        if slug in _NO_SLOT_SLUGS:
            pytest.skip("Decorative component — no slots expected")
        html = _read_html(slug)
        slots = _DATA_SLOT_RE.findall(html)
        assert len(slots) >= 1, f"{slug}: no data-slot attributes found"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_inline_font_family(self, slug: str) -> None:
        """Text-bearing elements have inline font-family."""
        html = _read_html(slug)
        # Check td elements that contain text (have data-slot or text content)
        text_tds = re.findall(
            r'<td[^>]*data-slot="[^"]*"[^>]*style="([^"]*)"',
            html,
            re.IGNORECASE,
        )
        for style in text_tds:
            # Skip hidden helper elements (e.g., VML fallback tds)
            if "display" in style.lower() and "none" in style.lower():
                continue
            assert "font-family" in style.lower(), f"{slug}: text td missing font-family in style"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_mso_conditional_on_complex(self, slug: str) -> None:
        """Complex components (grids, columns, cards) have MSO conditionals."""
        if slug not in _COMPLEX_SLUGS:
            pytest.skip("Not a complex multi-column component")
        html = _read_html(slug)
        assert "<!--[if mso]>" in html, f"{slug}: missing MSO conditional"


class TestNewComponentsInManifest:
    """Verify all new components load through the manifest pipeline."""

    def test_all_new_slugs_in_seeds(self) -> None:
        """All 61 new slugs appear in the loaded seeds."""
        seeds = load_file_components()
        loaded_slugs = {s["slug"] for s in seeds}
        missing = set(NEW_SLUGS) - loaded_slugs
        assert not missing, f"Missing from loaded seeds: {missing}"

    def test_new_component_count(self) -> None:
        """Manifest has at least 150 entries."""
        seeds = load_file_components()
        assert len(seeds) >= 150, f"Expected >=150, got {len(seeds)}"


_SLOT_SAMPLES: list[tuple[str, set[str]]] = [
    ("testimonial", {"quote", "author_name", "author_title", "avatar_url"}),
    ("pricing-table", {"plan_name", "price", "features", "cta_url", "cta_text"}),
    (
        "zigzag-image-left",
        {"image_url", "headline", "body", "cta_url", "cta_text"},
    ),
    ("event-card", {"event_name", "date", "location", "description", "cta_url", "cta_text"}),
    ("faq-list", {"heading", "faq_1_q", "faq_1_a", "faq_2_q", "faq_2_a", "faq_3_q", "faq_3_a"}),
]


class TestSlotFillIntegration:
    """Verify slot auto-detection works for representative new components."""

    @pytest.mark.parametrize(
        "slug,expected_slots",
        _SLOT_SAMPLES,
        ids=[s[0] for s in _SLOT_SAMPLES],
    )
    def test_slot_auto_detection(self, slug: str, expected_slots: set[str]) -> None:
        """Verify auto-detected slots match expected set."""
        seeds = load_file_components()
        seed = next((s for s in seeds if s["slug"] == slug), None)
        assert seed is not None, f"Seed {slug} not found"
        detected_ids = {s["slot_id"] for s in seed["slot_definitions"]}
        missing = expected_slots - detected_ids
        assert not missing, f"{slug}: missing auto-detected slots: {missing}"


class TestSecurityChecks:
    """Verify new component HTML has no security issues."""

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_no_script_tags(self, slug: str) -> None:
        html = _read_html(slug)
        assert "<script" not in html.lower(), f"{slug}: contains <script> tag"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_no_event_handlers(self, slug: str) -> None:
        html = _read_html(slug)
        handlers = re.findall(r"\bon\w+\s*=", html, re.IGNORECASE)
        # Filter out false positives like "one" in content
        real_handlers = [
            h
            for h in handlers
            if re.match(r"\bon(?:click|load|error|mouseover|focus|blur)\s*=", h, re.IGNORECASE)
        ]
        assert not real_handlers, f"{slug}: contains event handlers: {real_handlers}"

    @pytest.mark.parametrize("slug", NEW_SLUGS)
    def test_no_javascript_uris(self, slug: str) -> None:
        html = _read_html(slug)
        assert "javascript:" not in html.lower(), f"{slug}: contains javascript: URI"
