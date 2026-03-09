"""
Evaluation dimensions for each agent.

Following the generate-synthetic-data methodology:
- Define failure-prone axes of variation
- Create tuples (combinations) for test generation
- Each dimension targets where the agent is likely to fail
"""

# ---------------------------------------------------------------------------
# Scaffolder Agent Dimensions
# ---------------------------------------------------------------------------
SCAFFOLDER_DIMENSIONS = {
    "layout_complexity": {
        "description": "Structural complexity of the requested email layout",
        "values": [
            "single_column",
            "two_column",
            "three_column",
            "hero_plus_grid",
            "sidebar_layout",
            "nested_multi_section",
            "full_width_mixed",
        ],
    },
    "content_type": {
        "description": "Type of email campaign being built",
        "values": [
            "promotional_sale",
            "newsletter_digest",
            "transactional_receipt",
            "event_invitation",
            "abandoned_cart",
            "welcome_series",
            "product_launch",
            "re_engagement",
        ],
    },
    "client_quirk": {
        "description": "Email client compatibility challenge the template must handle",
        "values": [
            "outlook_mso_tables",
            "gmail_clipping_102kb",
            "yahoo_dark_mode",
            "apple_mail_retina",
            "outlook_vml_buttons",
            "no_special_quirks",
        ],
    },
    "brief_quality": {
        "description": "How well-specified the campaign brief is",
        "values": [
            "detailed_with_sections",
            "vague_one_liner",
            "contradictory_requirements",
            "overly_technical",
            "copy_heavy_no_structure",
        ],
    },
}

# ---------------------------------------------------------------------------
# Dark Mode Agent Dimensions
# ---------------------------------------------------------------------------
DARK_MODE_DIMENSIONS = {
    "input_html_complexity": {
        "description": "Structural complexity of the HTML being enhanced",
        "values": [
            "simple_single_column",
            "multi_column_nested_tables",
            "heavy_inline_styles",
            "mso_conditional_comments",
            "vml_elements_present",
            "mixed_mso_and_modern",
        ],
    },
    "color_scenario": {
        "description": "Color remapping challenge",
        "values": [
            "standard_light_theme",
            "already_dark_themed",
            "brand_colors_dominant",
            "gradient_backgrounds",
            "low_contrast_original",
            "many_unique_colors",
        ],
    },
    "outlook_challenge": {
        "description": "Outlook-specific dark mode behavior to handle",
        "values": [
            "data_ogsc_text_override",
            "data_ogsb_background_override",
            "vml_color_preservation",
            "mso_conditional_preservation",
            "outlook_android_dark",
            "no_outlook_issues",
        ],
    },
    "image_scenario": {
        "description": "Image-related dark mode handling needed",
        "values": [
            "logo_on_white_background",
            "transparent_png_logo",
            "dark_images_need_swap",
            "many_product_images",
            "no_images",
            "icons_need_inversion",
        ],
    },
}

# ---------------------------------------------------------------------------
# Content Agent Dimensions
# ---------------------------------------------------------------------------
CONTENT_DIMENSIONS = {
    "operation": {
        "description": "The copywriting operation requested",
        "values": [
            "subject_line",
            "preheader",
            "cta",
            "body_copy",
            "rewrite",
            "shorten",
            "expand",
            "tone_adjust",
        ],
    },
    "industry": {
        "description": "Industry vertical affecting tone and terminology",
        "values": [
            "ecommerce_fashion",
            "b2b_saas",
            "financial_services",
            "healthcare",
            "travel_hospitality",
            "food_beverage",
            "nonprofit",
            "real_estate",
        ],
    },
    "tone_target": {
        "description": "Desired tone for the output",
        "values": [
            "professional_formal",
            "casual_friendly",
            "urgent_fomo",
            "empathetic_supportive",
            "playful_witty",
            "authoritative_expert",
            "luxury_aspirational",
        ],
    },
    "constraint_pressure": {
        "description": "How constrained the content generation is",
        "values": [
            "tight_character_limit",
            "must_avoid_spam_words",
            "strict_brand_voice",
            "multilingual_context",
            "legal_compliance_required",
            "no_constraints",
        ],
    },
}

# ---------------------------------------------------------------------------
# Outlook Fixer Agent Dimensions
# ---------------------------------------------------------------------------
OUTLOOK_FIXER_DIMENSIONS = {
    "issue_type": {
        "description": "Category of Outlook rendering issue to fix",
        "values": [
            "ghost_table",
            "vml_background",
            "vml_button",
            "mso_conditional",
            "typography",
            "image_sizing",
            "table_gaps",
            "dpi_scaling",
            "max_width",
            "vml_namespace",
        ],
    },
    "element": {
        "description": "Specific HTML/VML element affected",
        "values": [
            "background_image",
            "bulletproof_button",
            "font_stack",
            "line_height",
            "table_spacing",
            "comment_matching",
            "namespace_declaration",
            "image_attributes",
            "layout_constraint",
        ],
    },
    "complexity": {
        "description": "Complexity of the fix required",
        "values": [
            "standard",
            "high",
            "multi_issue",
        ],
    },
}

# ---------------------------------------------------------------------------
# Accessibility Auditor Agent Dimensions
# ---------------------------------------------------------------------------
ACCESSIBILITY_DIMENSIONS = {
    "violation_category": {
        "description": "Category of WCAG violation present in the input HTML",
        "values": [
            "missing_alt_text",
            "decorative_img_no_empty_alt",
            "missing_lang_attribute",
            "layout_table_no_role",
            "low_contrast_text",
            "skipped_heading_levels",
            "non_descriptive_links",
            "missing_table_role",
            "color_only_information",
            "missing_document_title",
        ],
    },
    "html_complexity": {
        "description": "Structural complexity of the email HTML being audited",
        "values": [
            "simple_single_column",
            "multi_column_tables",
            "nested_layout_tables",
            "mso_conditional_heavy",
            "vml_elements_present",
            "mixed_layout_and_data_tables",
        ],
    },
    "image_scenario": {
        "description": "Type of image accessibility challenge",
        "values": [
            "informative_no_alt",
            "decorative_missing_empty_alt",
            "functional_link_image",
            "complex_infographic",
            "logo_with_text",
            "no_images",
        ],
    },
    "severity": {
        "description": "Mix of violation severity levels in the input",
        "values": [
            "single_critical",
            "multiple_moderate",
            "mixed_severity",
            "many_minor",
        ],
    },
}
