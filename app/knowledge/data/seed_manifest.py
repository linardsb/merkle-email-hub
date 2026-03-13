"""Manifest of seed documents for knowledge base."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SeedEntry:
    """A single seed document entry with metadata."""

    filename: str
    domain: str
    title: str
    description: str
    tags: list[str] = field(default_factory=lambda: list[str]())


ALLOWED_DOMAINS = {
    "css_support",
    "best_practices",
    "client_quirks",
    "email_ontology",
    "agent_references",
}

SEED_MANIFEST: list[SeedEntry] = [
    # --- CSS Support (8 documents) ---
    SeedEntry(
        filename="css_support/layout-properties.md",
        domain="css_support",
        title="CSS Layout Properties — Email Client Support",
        description="Compatibility matrix for display, position, float, flexbox, and grid across email clients.",
        tags=["css", "layout", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/box-model.md",
        domain="css_support",
        title="CSS Box Model — Email Client Support",
        description="Support matrix for margin, padding, width, height, max-width, and box-sizing.",
        tags=["css", "box-model", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/typography.md",
        domain="css_support",
        title="CSS Typography — Email Client Support",
        description="Font-family, font-size, line-height, text-decoration, and web font support.",
        tags=["css", "typography", "fonts", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/colors-backgrounds.md",
        domain="css_support",
        title="CSS Colors and Backgrounds — Email Client Support",
        description="Background-color, background-image, gradients, opacity, and rgba support.",
        tags=["css", "colors", "backgrounds", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/borders-shadows.md",
        domain="css_support",
        title="CSS Borders and Shadows — Email Client Support",
        description="Border-radius, box-shadow, outline, and border-collapse support.",
        tags=["css", "borders", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/media-queries.md",
        domain="css_support",
        title="CSS Media Queries — Email Client Support",
        description="@media support, prefers-color-scheme, max-width, and responsive email techniques.",
        tags=["css", "media-queries", "responsive", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/selectors.md",
        domain="css_support",
        title="CSS Selectors — Email Client Support",
        description="Pseudo-classes, attribute selectors, nth-child, and specificity in email clients.",
        tags=["css", "selectors", "compatibility"],
    ),
    SeedEntry(
        filename="css_support/dark-mode-css.md",
        domain="css_support",
        title="Dark Mode CSS — Email Client Support",
        description="color-scheme meta, prefers-color-scheme, data-ogsc/data-ogsb, and MSO overrides.",
        tags=["css", "dark-mode", "compatibility"],
    ),
    # --- Best Practices (6 documents) ---
    SeedEntry(
        filename="best_practices/table-based-layout.md",
        domain="best_practices",
        title="Table-Based Email Layout",
        description="Why tables are needed, nested table patterns, role=presentation, and width strategies.",
        tags=["layout", "tables", "best-practices"],
    ),
    SeedEntry(
        filename="best_practices/responsive-email.md",
        domain="best_practices",
        title="Responsive Email Design",
        description="Mobile-first approach, fluid hybrid method, media queries, and stacking patterns.",
        tags=["responsive", "mobile", "best-practices"],
    ),
    SeedEntry(
        filename="best_practices/image-optimization.md",
        domain="best_practices",
        title="Email Image Optimization",
        description="Image formats, dimensions, alt text, retina/HiDPI, and background image techniques.",
        tags=["images", "optimization", "best-practices"],
    ),
    SeedEntry(
        filename="best_practices/cta-buttons.md",
        domain="best_practices",
        title="Bulletproof CTA Buttons",
        description="Padding-based buttons, VML for Outlook, border-based approach, and accessibility.",
        tags=["buttons", "cta", "outlook", "best-practices"],
    ),
    SeedEntry(
        filename="best_practices/accessibility.md",
        domain="best_practices",
        title="Email Accessibility",
        description="Lang attribute, alt text, semantic tables, color contrast, and screen reader support.",
        tags=["accessibility", "wcag", "best-practices"],
    ),
    SeedEntry(
        filename="best_practices/file-size-optimization.md",
        domain="best_practices",
        title="Email File Size Optimization",
        description="Gmail 102KB clipping threshold, CSS inlining, redundant code removal, and minification.",
        tags=["file-size", "optimization", "gmail", "best-practices"],
    ),
    # --- Client Quirks (6 documents) ---
    SeedEntry(
        filename="client_quirks/outlook-windows.md",
        domain="client_quirks",
        title="Outlook Windows Rendering Quirks",
        description="Word rendering engine, MSO conditional comments, VML, DPI scaling, and table issues.",
        tags=["outlook", "windows", "rendering", "quirks"],
    ),
    SeedEntry(
        filename="client_quirks/gmail.md",
        domain="client_quirks",
        title="Gmail Rendering Quirks",
        description="CSS stripping, class renaming, style in head only, image proxying, and AMP support.",
        tags=["gmail", "css-stripping", "quirks"],
    ),
    SeedEntry(
        filename="client_quirks/apple-mail-ios.md",
        domain="client_quirks",
        title="Apple Mail and iOS Mail Rendering Quirks",
        description="WebKit rendering, dark mode auto-inversion, Dynamic Type, and data detectors.",
        tags=["apple-mail", "ios", "dark-mode", "quirks"],
    ),
    SeedEntry(
        filename="client_quirks/yahoo-mail.md",
        domain="client_quirks",
        title="Yahoo Mail Rendering Quirks",
        description="!important overrides, attribute selector support, class limitations, and CSS stripping.",
        tags=["yahoo", "css-stripping", "quirks"],
    ),
    SeedEntry(
        filename="client_quirks/samsung-mail.md",
        domain="client_quirks",
        title="Samsung Mail Rendering Quirks",
        description="Partial dark mode, font rendering, viewport quirks, and Android WebView behavior.",
        tags=["samsung", "android", "dark-mode", "quirks"],
    ),
    SeedEntry(
        filename="client_quirks/outlook-web.md",
        domain="client_quirks",
        title="Outlook.com and Office 365 Web Rendering Quirks",
        description="CSS subset differences, dark mode forced colors, class/id renaming, and safe styles.",
        tags=["outlook-web", "office-365", "dark-mode", "quirks"],
    ),
    # --- Agent References (9 documents) ---
    # L4 deep-reference docs used by agents via SKILL.md l4_sources pointers.
    # Symlinked from docs/SKILL_*.md into seeds/agent_references/.
    SeedEntry(
        filename="agent_references/SKILL_outlook-mso-fallback-reference.md",
        domain="agent_references",
        title="MSO Conditional & VML Fallback Reference",
        description="Complete MSO conditional comment patterns, VML backgrounds/buttons, ghost tables, DPI scaling, and Outlook version targeting for email HTML.",
        tags=["outlook", "mso", "vml", "fallback", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_html-email-css-dom-reference.md",
        domain="agent_references",
        title="HTML Email CSS DOM Reference",
        description="CSS property support across email clients, inline vs embedded strategies, vendor prefixes, and DOM-parsed validation rules.",
        tags=["css", "dom", "validation", "compatibility", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_html-email-components.md",
        domain="agent_references",
        title="HTML Email Component Patterns",
        description="Reusable email component patterns: headers, heroes, CTAs, footers, navigation, and table-based layout building blocks.",
        tags=["components", "layout", "patterns", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-spam-score-dom-reference.md",
        domain="agent_references",
        title="Email Spam Score DOM Reference",
        description="Spam trigger patterns, weighted scoring rules, word-boundary matching, formatting heuristics, and subject line risk factors.",
        tags=["spam", "deliverability", "triggers", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-link-validation-dom-reference.md",
        domain="agent_references",
        title="Email Link Validation DOM Reference",
        description="Link extraction patterns, URL format validation, ESP template syntax checking, empty href detection, and tracking parameter rules.",
        tags=["links", "validation", "url", "esp", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-image-optimization-dom-reference.md",
        domain="agent_references",
        title="Email Image Optimization DOM Reference",
        description="Image dimension validation, format support, alt text rules, tracking pixel accessibility, data URI sizing, and retina/HiDPI patterns.",
        tags=["images", "optimization", "alt-text", "dimensions", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-file-size-guidelines.md",
        domain="agent_references",
        title="Email File Size Guidelines",
        description="Multi-client size thresholds (Gmail 102KB, Yahoo 75KB, Outlook 100KB), content breakdown analysis, gzip estimation, and minification strategies.",
        tags=["file-size", "optimization", "gmail", "clipping", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-dark-mode-dom-reference.md",
        domain="agent_references",
        title="Email Dark Mode DOM Reference",
        description="Color-scheme meta tags, prefers-color-scheme media queries, Outlook data-ogsc/data-ogsb selectors, color remapping, and image swap patterns.",
        tags=["dark-mode", "meta-tags", "color-scheme", "outlook", "agent-reference"],
    ),
    SeedEntry(
        filename="agent_references/SKILL_email-accessibility-wcag-aa.md",
        domain="agent_references",
        title="Email Accessibility WCAG AA Reference",
        description="WCAG 2.1 AA compliance rules for email: alt text quality, color contrast ratios, semantic structure, table roles, heading hierarchy, and ARIA attributes.",
        tags=["accessibility", "wcag", "alt-text", "contrast", "agent-reference"],
    ),
]
