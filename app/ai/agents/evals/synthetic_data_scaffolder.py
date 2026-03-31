"""Synthetic test data for the Scaffolder agent.

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
    # =========================================================================
    # Template Selection Edge Cases (11.22.9)
    # =========================================================================
    # -------------------------------------------------------------------------
    # 13. Ambiguous brief — could be newsletter or promotional
    # -------------------------------------------------------------------------
    {
        "id": "scaff-013",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "newsletter_digest",
            "client_quirk": "no_special_quirks",
            "brief_quality": "vague_one_liner",
            "template_selection_accuracy": "ambiguous",
        },
        "brief": (
            "We need an email about our latest product updates and a 20% discount "
            "for existing customers. Mix of news and promotion."
        ),
        "expected_challenges": [
            "ambiguous intent — newsletter vs promotional",
            "agent must pick a reasonable template for hybrid content",
            "should not fail due to ambiguity",
        ],
    },
    # -------------------------------------------------------------------------
    # 14. Multi-intent brief — newsletter + CTA + event
    # -------------------------------------------------------------------------
    {
        "id": "scaff-014",
        "dimensions": {
            "layout_complexity": "two_column",
            "content_type": "newsletter_digest",
            "client_quirk": "no_special_quirks",
            "brief_quality": "detailed_with_sections",
            "template_selection_accuracy": "reasonable_choice",
        },
        "brief": (
            "Monthly update email that includes: 1) Company news article, "
            "2) Product spotlight with buy CTA, 3) Upcoming webinar invitation "
            "with registration button, 4) Customer testimonial quote. "
            "This serves as newsletter, promotional, and event invite combined."
        ),
        "expected_challenges": [
            "multi-intent brief spanning 3 template categories",
            "agent must select best-fit template for dominant intent",
            "all sections should be accommodated",
        ],
    },
    # -------------------------------------------------------------------------
    # 15. Novel layout request — no single template fits
    # -------------------------------------------------------------------------
    {
        "id": "scaff-015",
        "dimensions": {
            "layout_complexity": "full_width_mixed",
            "content_type": "product_launch",
            "client_quirk": "outlook_vml_buttons",
            "brief_quality": "detailed_with_sections",
            "template_selection_accuracy": "novel_layout",
        },
        "brief": (
            "Interactive product showcase with: full-width video placeholder (600x338), "
            "tabbed content area showing 3 product variants side-by-side with comparison "
            "table, accordion FAQ section, floating sticky CTA bar at bottom, "
            "and a dynamically-generated color swatch grid (4x3). "
            "This is a unique layout not matching any standard template."
        ),
        "expected_challenges": [
            "should trigger __compose__ mode or fallback",
            "agent must handle gracefully when no template matches",
            "still produce valid email HTML despite novel requirements",
        ],
    },
    # -------------------------------------------------------------------------
    # 16. Contradictory requirements — simple + complex
    # -------------------------------------------------------------------------
    {
        "id": "scaff-016",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "promotional_sale",
            "client_quirk": "no_special_quirks",
            "brief_quality": "contradictory_requirements",
            "template_selection_accuracy": "ambiguous",
        },
        "brief": (
            "Create a simple, minimal email with just a headline and one CTA. "
            "But also include 12 product cards, a carousel, countdown timer, "
            "social proof section with 5 reviews, and an interactive size guide. "
            "Keep it under 30KB."
        ),
        "expected_challenges": [
            "contradictory: minimal vs feature-heavy",
            "agent must resolve to a sensible template choice",
            "should prioritize deliverability over feature requests",
        ],
    },
    # -------------------------------------------------------------------------
    # 17. Minimal brief — tests default template selection
    # -------------------------------------------------------------------------
    {
        "id": "scaff-017",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "welcome_series",
            "client_quirk": "no_special_quirks",
            "brief_quality": "vague_one_liner",
            "template_selection_accuracy": "ambiguous",
        },
        "brief": "make email",
        "expected_challenges": [
            "near-zero context brief",
            "agent must fall back to a sensible default template",
            "should produce valid HTML despite minimal input",
        ],
    },
    # -------------------------------------------------------------------------
    # 18. Exact template match — promotional hero
    # -------------------------------------------------------------------------
    {
        "id": "scaff-018",
        "dimensions": {
            "layout_complexity": "hero_plus_grid",
            "content_type": "promotional_sale",
            "client_quirk": "no_special_quirks",
            "brief_quality": "detailed_with_sections",
            "template_selection_accuracy": "exact_match",
        },
        "brief": (
            "Flash sale email with a large hero banner at the top showing "
            "'48 Hour Flash Sale — Up to 60% Off'. Below the hero, a 2-column "
            "grid of 4 featured products with images, names, and prices. "
            "Single CTA button: 'Shop the Sale'. Footer with unsubscribe."
        ),
        "expected_challenges": [
            "should clearly map to promotional_hero template",
            "template selection should be deterministic for this brief",
            "slot fills should align with template structure",
        ],
    },
    # -------------------------------------------------------------------------
    # 19. Exact match — transactional shipping
    # -------------------------------------------------------------------------
    {
        "id": "scaff-019",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "transactional_receipt",
            "client_quirk": "outlook_mso_tables",
            "brief_quality": "detailed_with_sections",
            "template_selection_accuracy": "exact_match",
        },
        "brief": (
            "Shipping confirmation email: 'Your order has shipped!' "
            "Include tracking number, carrier name, estimated delivery date, "
            "order summary (1-3 items with thumbnails), and a 'Track Package' CTA. "
            "Clean, transactional layout — no promotional content."
        ),
        "expected_challenges": [
            "should map to transactional_shipping template",
            "must not select promotional or newsletter template",
            "transactional tone, no upsell",
        ],
    },
    # -------------------------------------------------------------------------
    # 20. Brief with strong brand constraints — slot fill quality test
    # -------------------------------------------------------------------------
    {
        "id": "scaff-020",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "event_invitation",
            "client_quirk": "no_special_quirks",
            "brief_quality": "detailed_with_sections",
            "slot_fill_quality": "complete",
        },
        "brief": (
            "Webinar invitation for 'AI in Email Marketing' on April 15, 2025 at 2pm EST. "
            "Speaker: Dr. Sarah Chen, VP of AI at TechCorp. "
            "Include event title, date/time, speaker bio (2 sentences), "
            "3 key takeaways as bullet points, and a 'Reserve Your Spot' CTA. "
            "Brand colors: #1A1A2E primary, #E94560 accent. Font: Inter."
        ),
        "expected_challenges": [
            "all slot content clearly specified — no ambiguity",
            "slot fills should capture every detail from brief",
            "design tokens should use specified brand colors",
        ],
    },
    # -------------------------------------------------------------------------
    # 21. Mismatched slot expectations — retention survey
    # -------------------------------------------------------------------------
    {
        "id": "scaff-021",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "re_engagement",
            "client_quirk": "no_special_quirks",
            "brief_quality": "copy_heavy_no_structure",
            "slot_fill_quality": "partial",
        },
        "brief": (
            "Hey we need a survey email. Ask customers to rate their experience "
            "from 1-5 stars and leave a comment. Also mention our new rewards program "
            "and remind them about free shipping on orders over $75. Oh and there's "
            "a store locator link somewhere. The CEO wants to include a personal note "
            "at the top but hasn't written it yet — use placeholder text for now."
        ),
        "expected_challenges": [
            "mixed intent: survey + promotional + transactional",
            "CEO note is a placeholder — partial slot fill expected",
            "agent must structure freeform into coherent template slots",
        ],
    },
    # -------------------------------------------------------------------------
    # 22. Design token coherence — contrast edge case
    # -------------------------------------------------------------------------
    {
        "id": "scaff-022",
        "dimensions": {
            "layout_complexity": "single_column",
            "content_type": "announcement_company",
            "client_quirk": "yahoo_dark_mode",
            "brief_quality": "detailed_with_sections",
            "design_token_coherence": "contrast_violation",
        },
        "brief": (
            "Company announcement email. Brand colors: light yellow #FFFACD background "
            "with light gray #C0C0C0 text. Header uses white text on pale blue #ADD8E6. "
            "CTA button: light pink #FFB6C1 with white text. "
            "These colors fail WCAG contrast — agent should detect and fix."
        ),
        "expected_challenges": [
            "brand colors have low contrast ratios",
            "agent should flag or auto-correct contrast violations",
            "dark mode variant must also maintain contrast",
        ],
    },
    # =========================================================================
    # DESIGN FIDELITY CASES — backed by real training HTML from
    # email-templates/training_HTML/for_converter_engine/
    # These cases carry design_context with Figma metadata for the
    # design_fidelity judge criterion (eval-only, not used in live builds).
    # =========================================================================
    # -------------------------------------------------------------------------
    # 23. Design fidelity — Starbucks Pumpkin Spice (9 sections)
    # -------------------------------------------------------------------------
    {
        "id": "scaff-023",
        "dimensions": {
            "layout_complexity": "mixed_multi_section",
            "content_type": "promotional_seasonal",
            "client_quirk": "outlook_vml_buttons",
            "brief_quality": "detailed_with_sections",
            "design_fidelity": "full_figma_context",
        },
        "brief": (
            "Starbucks seasonal promotional email: Pumpkin Now, Peppermint On The Way. "
            "9 sections: full-width hero image, centered heading (40px, #1e3932 on #F2F0EB), "
            "italic body paragraph, VML pill CTA button (#1e3932, 25px radius), "
            "two-column holiday countdown (image left, text right on #AA1733 red), "
            "four-column icon navigation bar (#296042 dark green, image-based), "
            "social icons row, legal footer (7 rows), Starbucks Rewards logo. "
            "Font: SoDo Sans. Dark mode: full component dark mode class system."
        ),
        "expected_challenges": [
            "color_fidelity",
            "font_override",
            "section_mapping",
            "VML bulletproof button with pill shape",
            "asymmetric two-column layout",
            "image-based navigation with 2x2 mobile reflow",
        ],
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1424",
            "node_id": "2833-1424",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "background": "#F2F0EB",
                    "primary_text": "#1e3932",
                    "cta_fill": "#1e3932",
                    "holiday_red": "#AA1733",
                    "nav_green": "#296042",
                    "footer_text": "#707070",
                },
                "fonts": {
                    "heading": "SoDo Sans",
                    "body": "SoDo Sans",
                    "serif_accent": "Lander Grande",
                },
                "font_sizes": {
                    "heading": "40px",
                    "body": "16px",
                    "cta": "16px",
                    "footer": "11px",
                },
                "spacing": {
                    "heading_padding_top": "40px",
                    "cta_padding_bottom": "40px",
                    "social_padding_top": "30px",
                },
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {
                    "section_index": 1,
                    "component_slug": "heading",
                    "figma_frame_name": "Heading",
                    "style_overrides": {
                        "bgcolor": "#F2F0EB",
                        "color": "#1e3932",
                        "font-size": "40px",
                    },
                },
                {
                    "section_index": 2,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Body Text",
                    "style_overrides": {"font-style": "italic", "color": "#1e3932"},
                },
                {
                    "section_index": 3,
                    "component_slug": "button-filled",
                    "figma_frame_name": "CTA Button",
                    "style_overrides": {"background-color": "#1e3932", "border-radius": "25px"},
                },
                {
                    "section_index": 4,
                    "component_slug": "column-layout-2",
                    "figma_frame_name": "Holiday Countdown",
                    "style_overrides": {"bgcolor": "#AA1733"},
                },
                {
                    "section_index": 5,
                    "component_slug": "column-layout-4",
                    "figma_frame_name": "Nav Bar",
                    "style_overrides": {"bgcolor": "#296042"},
                },
                {
                    "section_index": 6,
                    "component_slug": "footer-social",
                    "figma_frame_name": "Social Icons",
                },
                {
                    "section_index": 7,
                    "component_slug": "footer",
                    "figma_frame_name": "Legal Footer",
                },
                {"section_index": 8, "component_slug": "image", "figma_frame_name": "Rewards Logo"},
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 24. Design fidelity — Mammut Duvet Day (18 sections)
    # -------------------------------------------------------------------------
    {
        "id": "scaff-024",
        "dimensions": {
            "layout_complexity": "complex_multi_section",
            "content_type": "promotional_ecommerce",
            "client_quirk": "outlook_vml_buttons",
            "brief_quality": "detailed_with_sections",
            "design_fidelity": "full_figma_context",
        },
        "brief": (
            "Mammut outdoor brand email: Grab A Duvet Day. 18 sections: "
            "hero image (climber), heading (#E85D26 orange bg, white text, 32px, uppercase), "
            "body paragraph (white on orange), ghost CTA button (white border on orange, VML, sharp corners), "
            "full-width product image, product heading, product paragraph, product CTA, "
            "second product image, second product heading + paragraph + CTA, "
            "vertical navigation bar (4 links with border separators), "
            "three-column social icons with text labels, simple footer. "
            "Dark mode: class-based (.dark-mode), not auto prefers-color-scheme. "
            "System font stack (no custom font). Extra mobile classes: .prod-gutter, .prod-row."
        ),
        "expected_challenges": [
            "color_fidelity",
            "18_section_structure",
            "class_based_dark_mode",
            "VML ghost button sharp corners",
            "vertical navigation bar pattern",
        ],
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1135",
            "node_id": "2833-1135",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "primary_orange": "#E85D26",
                    "heading_text": "#ffffff",
                    "body_text": "#ffffff",
                    "body_bg_default": "#ffffff",
                    "product_heading": "#1A1A1A",
                },
                "fonts": {
                    "heading": "system-ui",
                    "body": "system-ui",
                },
                "font_sizes": {
                    "heading": "32px",
                    "body": "14px",
                    "nav_link": "16px",
                },
                "spacing": {
                    "heading_padding_top": "30px",
                    "body_padding_top": "16px",
                },
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {
                    "section_index": 1,
                    "component_slug": "heading",
                    "figma_frame_name": "Heading",
                    "style_overrides": {"bgcolor": "#E85D26", "color": "#ffffff"},
                },
                {
                    "section_index": 2,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Body Text",
                    "style_overrides": {"bgcolor": "#E85D26", "color": "#ffffff"},
                },
                {
                    "section_index": 3,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Ghost CTA",
                    "style_overrides": {"border-radius": "0%", "bgcolor": "#E85D26"},
                },
                {
                    "section_index": 4,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Product Image 1",
                },
                {
                    "section_index": 5,
                    "component_slug": "heading",
                    "figma_frame_name": "Product Heading 1",
                },
                {
                    "section_index": 6,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Product Body 1",
                },
                {
                    "section_index": 7,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Product CTA 1",
                },
                {
                    "section_index": 8,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Product Image 2",
                },
                {
                    "section_index": 9,
                    "component_slug": "heading",
                    "figma_frame_name": "Product Heading 2",
                },
                {
                    "section_index": 10,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Product Body 2",
                },
                {
                    "section_index": 11,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Product CTA 2",
                },
                {
                    "section_index": 12,
                    "component_slug": "navigation-bar",
                    "figma_frame_name": "Vertical Nav",
                },
                {
                    "section_index": 13,
                    "component_slug": "column-layout-3",
                    "figma_frame_name": "Social Icons",
                },
                {"section_index": 14, "component_slug": "footer", "figma_frame_name": "Footer"},
            ],
        },
    },
    # -------------------------------------------------------------------------
    # 25. Design fidelity — MAAP x KASK (13 sections)
    # -------------------------------------------------------------------------
    {
        "id": "scaff-025",
        "dimensions": {
            "layout_complexity": "mixed_multi_section",
            "content_type": "promotional_collaboration",
            "client_quirk": "outlook_vml_buttons",
            "brief_quality": "detailed_with_sections",
            "design_fidelity": "full_figma_context",
        },
        "brief": (
            "MAAP x KASK cycling brand collaboration email. 13 sections: "
            "full-width hero image, subtitle heading (12px #555555 category label), "
            "main heading (36px #101828, 800 weight), body paragraph (16px #555555), "
            "ghost pill CTA button (25px radius, 1px solid #222222), "
            "two-column product images with 4px gutter, divider (#e0e0e0), "
            "vertical navigation bar (26px, 800 weight, arrow &#8599;), "
            "second divider, store locator pill button grid (7 city pills), "
            "three-column feature icons on #f7f7f7, dark footer (#000000 bg). "
            "Font: system stack. Dark mode: class-based with textblock-heading/body classes."
        ),
        "expected_challenges": [
            "color_fidelity",
            "monochrome_palette",
            "pill_button_grid_composite",
            "vertical_navigation_pattern",
            "dark_footer",
        ],
        "design_context": {
            "figma_url": "https://www.figma.com/design/VUlWjZGAEVZr3mK1EawsYR/The-Ultimate-Email-Design-System--Community-?node-id=2833-1623",
            "node_id": "2833-1623",
            "file_id": "VUlWjZGAEVZr3mK1EawsYR",
            "design_tokens": {
                "colors": {
                    "heading_text": "#101828",
                    "body_text": "#555555",
                    "subtitle_text": "#555555",
                    "button_border": "#222222",
                    "divider": "#e0e0e0",
                    "feature_bg": "#f7f7f7",
                    "footer_bg": "#000000",
                    "footer_link": "#cccccc",
                    "pill_bg": "#222222",
                },
                "fonts": {
                    "heading": "system-ui",
                    "body": "system-ui",
                },
                "font_sizes": {
                    "subtitle": "12px",
                    "heading": "36px",
                    "body": "16px",
                    "nav_link": "26px",
                    "pill": "12px",
                },
                "spacing": {
                    "subtitle_padding_top": "16px",
                    "heading_padding_top": "8px",
                    "body_padding_top": "12px",
                    "divider_padding": "34px",
                    "footer_padding": "40px 44px",
                },
            },
            "section_mapping": [
                {
                    "section_index": 0,
                    "component_slug": "full-width-image",
                    "figma_frame_name": "Hero Image",
                },
                {
                    "section_index": 1,
                    "component_slug": "heading",
                    "figma_frame_name": "Subtitle",
                    "style_overrides": {"font-size": "12px", "color": "#555555"},
                },
                {
                    "section_index": 2,
                    "component_slug": "heading",
                    "figma_frame_name": "Main Heading",
                    "style_overrides": {"font-size": "36px", "font-weight": "800"},
                },
                {
                    "section_index": 3,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Body Text",
                    "style_overrides": {"color": "#555555"},
                },
                {
                    "section_index": 4,
                    "component_slug": "button-ghost",
                    "figma_frame_name": "Discover CTA",
                    "style_overrides": {"border-radius": "25px"},
                },
                {
                    "section_index": 5,
                    "component_slug": "column-layout-2",
                    "figma_frame_name": "Product Images",
                },
                {"section_index": 6, "component_slug": "divider", "figma_frame_name": "Divider 1"},
                {
                    "section_index": 7,
                    "component_slug": "navigation-bar",
                    "figma_frame_name": "Vertical Nav",
                    "style_overrides": {"font-size": "26px", "font-weight": "800"},
                },
                {"section_index": 8, "component_slug": "divider", "figma_frame_name": "Divider 2"},
                {
                    "section_index": 9,
                    "component_slug": "paragraph",
                    "figma_frame_name": "Store Locator",
                },
                {
                    "section_index": 10,
                    "component_slug": "column-layout-3",
                    "figma_frame_name": "Feature Icons",
                    "style_overrides": {"bgcolor": "#f7f7f7"},
                },
                {
                    "section_index": 11,
                    "component_slug": "footer",
                    "figma_frame_name": "Dark Footer",
                    "style_overrides": {"bgcolor": "#000000"},
                },
            ],
        },
    },
]
