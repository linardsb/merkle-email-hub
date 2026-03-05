"""
Synthetic test data for the Scaffolder agent.

Each test case is a tuple of (dimensions, brief, expected_challenges).
Briefs use realistic campaign language. Expected challenges guide evaluation.
"""

SCAFFOLDER_TEST_CASES = [
    # -------------------------------------------------------------------------
    # 1. Simple single-column promotional — baseline happy path
    # -------------------------------------------------------------------------
    {
        "id": "scaff-001",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "promotional_sale",
            "client_quirk": "no_special_quirks",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Create a single-column promotional email for our Summer Sale event. "
            "Header: full-width hero image (600x300) with overlay text 'Summer Sale — Up to 50% Off'. "
            "Body: 3 product cards stacked vertically, each with product image (280x280), "
            "name, price (strikethrough old price + new price), and a 'Shop Now' CTA button. "
            "Footer: social icons row, unsubscribe link, company address. "
            "Brand colors: primary #FF6B35, secondary #004E89, background #FFFFFF. "
            "Font: Arial, fallback Helvetica."
        ),
        "expected_challenges": [
            "correct table-based layout",
            "proper image alt text",
            "CTA buttons with VML fallback",
        ],
    },
    # -------------------------------------------------------------------------
    # 2. Two-column newsletter with Outlook ghost tables
    # -------------------------------------------------------------------------
    {
        "id": "scaff-002",
        "dimensions": {
            "layout_complexity": "two_column",
            "content_type": "newsletter_digest",
            "client_quirk": "outlook_mso_tables",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Build a two-column newsletter digest. Left column (60%): 3 article summaries with "
            "thumbnail (180x120), headline, 2-line excerpt, and 'Read More' link. "
            "Right column (40%): sidebar with upcoming events list (date + title, 4 items) "
            "and a 'Subscribe to Calendar' CTA. "
            "Must work perfectly in Outlook 2016/2019 — use MSO ghost tables:\n"
            '<!--[if mso]><table role="presentation" cellspacing="0" cellpadding="0" '
            'border="0" width="100%"><tr><td width="340"><![endif]-->\n'
            "...left column...\n"
            '<!--[if mso]></td><td width="260"><![endif]-->\n'
            "...right column...\n"
            "<!--[if mso]></td></tr></table><![endif]-->\n"
            "Header: company logo centered, navigation links. "
            "Footer: social links, preferences link, unsubscribe."
        ),
        "expected_challenges": [
            "MSO conditional ghost tables for 2-col layout",
            "proper width attributes on tables and tds",
            "cellpadding=0 cellspacing=0 on all tables",
            "responsive stacking on mobile",
        ],
    },
    # -------------------------------------------------------------------------
    # 3. Three-column product grid — Gmail clipping risk
    # -------------------------------------------------------------------------
    {
        "id": "scaff-003",
        "dimensions": {
            "layout_complexity": "three_column",
            "content_type": "product_launch",
            "client_quirk": "gmail_clipping_102kb",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Product launch email with a 3-column grid showcasing our new collection. "
            "Hero section: full-width image with 'New Arrivals' heading. "
            "3-column product grid (2 rows = 6 products): each cell has product image (180x200), "
            "product name, price, and mini CTA. "
            "CRITICAL: keep total HTML under 102KB to avoid Gmail clipping. "
            "Use compact code — minimize whitespace and comments. "
            "Each column should be ~33% width in a nested table structure:\n"
            '<table width="600"><tr>\n'
            '  <td width="33%" valign="top">...</td>\n'
            '  <td width="33%" valign="top">...</td>\n'
            '  <td width="34%" valign="top">...</td>\n'
            "</tr></table>\n"
            "Include dark mode meta tags and basic dark mode CSS."
        ),
        "expected_challenges": [
            "compact HTML to stay under 102KB",
            "3-column nested table layout",
            "dark mode meta tags included",
            "proper width distribution",
        ],
    },
    # -------------------------------------------------------------------------
    # 4. Hero + grid layout with VML bulletproof buttons
    # -------------------------------------------------------------------------
    {
        "id": "scaff-004",
        "dimensions": {
            "layout_complexity": "hero_plus_grid",
            "content_type": "event_invitation",
            "client_quirk": "outlook_vml_buttons",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Event invitation email for our annual tech conference 'DevSummit 2025'. "
            "Hero: full-width background image (600x400) with event title, date, location overlaid. "
            "Use VML for bulletproof background image in Outlook:\n"
            "<!--[if gte mso 9]>\n"
            '<v:rect xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false" '
            'style="width:600px;height:400px;">\n'
            '<v:fill type="frame" src="hero-bg.jpg" />\n'
            '<v:textbox inset="0,0,0,0">\n'
            "<![endif]-->\n"
            "Below hero: 2x2 grid of speaker cards with headshot, name, title, topic. "
            "Primary CTA: 'Register Now' — must be a VML roundrect button for Outlook:\n"
            "<!--[if mso]>\n"
            '<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" '
            'href="https://example.com/register" '
            'style="height:44px;v-text-anchor:middle;width:200px;" '
            'arcsize="10%" strokecolor="#FF6B35" fillcolor="#FF6B35">\n'
            "<w:anchorlock/>\n"
            '<center style="color:#ffffff;font-family:Arial;font-size:16px;">'
            "Register Now</center>\n"
            "</v:roundrect>\n"
            "<![endif]-->\n"
            "Include xmlns:v and xmlns:o namespaces on html tag."
        ),
        "expected_challenges": [
            "VML background image in hero",
            "VML roundrect button",
            "xmlns:v and xmlns:o namespaces",
            "proper nested table grid for speakers",
        ],
    },
    # -------------------------------------------------------------------------
    # 5. Transactional receipt — minimal styling, heavy structure
    # -------------------------------------------------------------------------
    {
        "id": "scaff-005",
        "dimensions": {
            "layout_complexity": "nested_multi_section",
            "content_type": "transactional_receipt",
            "client_quirk": "outlook_mso_tables",
            "brief_quality": "overly_technical",
        },
        "brief": (
            "Order confirmation email. Structure: "
            "1) Logo + order number header "
            "2) Shipping address block "
            "3) Order items table with columns: item image (60x60), name, qty, price "
            "4) Subtotal/shipping/tax/total summary aligned right "
            "5) Shipping tracking CTA "
            "6) Help/returns footer. "
            "Use role=presentation on all layout tables. "
            "Use mso-line-height-rule:exactly on all tds. "
            "Ensure DPI scaling fix for Outlook:\n"
            "<!--[if gte mso 9]>\n"
            "<xml>\n"
            "<o:OfficeDocumentSettings>\n"
            "<o:AllowPNG/>\n"
            "<o:PixelsPerInch>96</o:PixelsPerInch>\n"
            "</o:OfficeDocumentSettings>\n"
            "</xml>\n"
            "<![endif]-->"
        ),
        "expected_challenges": [
            "complex nested table structure",
            "DPI scaling fix for Outlook",
            "mso-line-height-rule: exactly",
            "proper data table for order items",
            "role=presentation on layout tables",
        ],
    },
    # -------------------------------------------------------------------------
    # 6. Vague brief — tests agent's ability to handle ambiguity
    # -------------------------------------------------------------------------
    {
        "id": "scaff-006",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "welcome_series",
            "client_quirk": "no_special_quirks",
            "brief_quality": "vague_one_liner",
        },
        "brief": "Make a welcome email for new subscribers.",
        "expected_challenges": [
            "agent must infer reasonable defaults",
            "should still produce valid Maizzle template",
            "should include basic structure despite vague brief",
        ],
    },
    # -------------------------------------------------------------------------
    # 7. Contradictory brief — tests robustness
    # -------------------------------------------------------------------------
    {
        "id": "scaff-007",
        "dimensions": {
            "layout_complexity": "two_column",
            "content_type": "promotional_sale",
            "client_quirk": "no_special_quirks",
            "brief_quality": "contradictory_requirements",
        },
        "brief": (
            "Create a minimalist email with lots of whitespace and a clean design. "
            "Include 8 product images, 4 banner sections, 3 CTA buttons, "
            "a countdown timer, animated GIF header, and an embedded video. "
            "Keep total file size under 50KB. "
            "Use only system fonts but also include our custom webfont 'BrandSerif'. "
            "Make it work in all email clients including Lotus Notes."
        ),
        "expected_challenges": [
            "agent must resolve contradictions sensibly",
            "should prioritize email client compatibility",
            "should not include script or embed tags",
            "should flag impossible requirements",
        ],
    },
    # -------------------------------------------------------------------------
    # 8. Abandoned cart with personalization tokens
    # -------------------------------------------------------------------------
    {
        "id": "scaff-008",
        "dimensions": {
            "layout_complexity": "hero_plus_grid",
            "content_type": "abandoned_cart",
            "client_quirk": "no_special_quirks",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Abandoned cart reminder email. "
            "Header: 'You left something behind, {{first_name}}!' "
            "Hero: lifestyle image with overlay text. "
            "Cart items section: dynamic block showing 1-3 cart items — "
            "use placeholder for each: image (120x120), item name, size/color, price. "
            "Urgency bar: 'Items in your cart are selling fast' with subtle animation. "
            "Primary CTA: 'Complete Your Order' button. "
            "Secondary: 'Continue Shopping' text link. "
            "Include preheader: 'Your cart is waiting — complete your order before items sell out.' "
            "Footer: standard unsubscribe + company info."
        ),
        "expected_challenges": [
            "Maizzle template variable syntax",
            "dynamic/repeated content blocks",
            "urgency without spam patterns",
            "proper preheader implementation",
        ],
    },
    # -------------------------------------------------------------------------
    # 9. Re-engagement with Apple Mail retina considerations
    # -------------------------------------------------------------------------
    {
        "id": "scaff-009",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "re_engagement",
            "client_quirk": "apple_mail_retina",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Win-back email for inactive subscribers (90+ days). "
            "Tone: warm, not desperate. "
            "Hero: illustration-style image (provide 2x retina version at 1200x600, "
            "display at 600x300 with width/height attributes). "
            "Body: 'We miss you' headline, brief value recap (3 bullet points), "
            "exclusive 20% off comeback offer with code display. "
            "CTA: 'Come Back & Save 20%'. "
            "All images must have explicit width AND height attributes for retina rendering. "
            "Include srcset for Apple Mail if possible."
        ),
        "expected_challenges": [
            "retina image handling with width/height attrs",
            "proper image dimensions (display vs actual)",
            "warm tone in template structure",
        ],
    },
    # -------------------------------------------------------------------------
    # 10. Full-width mixed layout with Yahoo dark mode issues
    # -------------------------------------------------------------------------
    {
        "id": "scaff-010",
        "dimensions": {
            "layout_complexity": "full_width_mixed",
            "content_type": "newsletter_digest",
            "client_quirk": "yahoo_dark_mode",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Weekly tech newsletter with mixed full-width and contained sections. "
            "Full-width colored banner (#004E89) with white text headline. "
            "600px contained body: featured article (image left, text right), "
            "3 news briefs stacked, and a 'Quick Links' section. "
            "Full-width gradient footer. "
            "IMPORTANT: Yahoo Mail forces dark mode differently — add both:\n"
            "@media (prefers-color-scheme: dark) { ... }\n"
            "AND class-based overrides that Yahoo can parse. "
            "Include meta color-scheme tags. "
            "Use dark mode utility classes on key elements."
        ),
        "expected_challenges": [
            "full-width vs contained width sections",
            "dark mode CSS for Yahoo compatibility",
            "meta color-scheme tags",
            "colored banner that works in dark mode",
        ],
    },
    # -------------------------------------------------------------------------
    # 11. Copy-heavy brief with no structure guidance
    # -------------------------------------------------------------------------
    {
        "id": "scaff-011",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "promotional_sale",
            "client_quirk": "no_special_quirks",
            "brief_quality": "copy_heavy_no_structure",
        },
        "brief": (
            "Hey so we need an email for our Black Friday sale. We're doing 30% off everything "
            "plus free shipping over $50. The sale starts November 28 at midnight and ends "
            "December 1. We have some hero products to feature — the UltraComfort Hoodie ($89 "
            "now $62.30), the All-Terrain Boot ($140 now $98), and the Everyday Backpack ($65 "
            "now $45.50). We also want to mention our gift guide and that we have gift cards "
            "available. Oh and our loyalty members get early access starting Nov 27. The subject "
            "line should be something about Black Friday but not too spammy. Our brand colors "
            "are black and gold (#C9A84C). Make it look premium not discount-y."
        ),
        "expected_challenges": [
            "agent must extract structure from freeform text",
            "organize products into visual layout",
            "balance premium feel with sale messaging",
            "avoid spam trigger words",
        ],
    },
    # -------------------------------------------------------------------------
    # 12. Sidebar layout with complex MSO + accessibility
    # -------------------------------------------------------------------------
    {
        "id": "scaff-012",
        "dimensions": {
            "layout_complexity": "sidebar_layout",
            "content_type": "newsletter_digest",
            "client_quirk": "outlook_mso_tables",
            "brief_quality": "detailed_with_sections",
        },
        "brief": (
            "Monthly investor update email with sidebar navigation. "
            "Left sidebar (200px): table of contents links — Q3 Results, Market Update, "
            "Portfolio Changes, Upcoming Events, Team Notes. "
            "Main content (400px): each section with heading, paragraph, optional chart image. "
            "ACCESSIBILITY REQUIREMENTS: "
            "- lang attribute on html tag "
            "- role=article and aria-roledescription=email on wrapper "
            "- role=presentation on ALL layout tables "
            "- semantic heading hierarchy h1 > h2 > h3 "
            "- 4.5:1 minimum contrast ratio "
            "- meaningful alt text on all images "
            "- skip-to-content link for screen readers "
            "Wrap in MSO ghost table for Outlook sidebar rendering."
        ),
        "expected_challenges": [
            "sidebar + main content MSO ghost table",
            "full accessibility compliance",
            "semantic heading hierarchy",
            "skip navigation for screen readers",
        ],
    },
]
