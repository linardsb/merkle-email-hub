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
    "output_length": {
        "description": "Output length behavior being tested",
        "values": [
            "within_limits",
            "at_boundary",
            "over_max",
            "under_min",
            "ratio_violation",
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
            "landmark_roles",
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

# ---------------------------------------------------------------------------
# Personalisation Agent Dimensions
# ---------------------------------------------------------------------------
PERSONALISATION_DIMENSIONS = {
    "esp_platform": {
        "description": "Target ESP platform for personalisation syntax",
        "values": [
            "braze",
            "sfmc",
            "adobe_campaign",
        ],
    },
    "variable_complexity": {
        "description": "Complexity of variables and data references",
        "values": [
            "basic_field",
            "custom_attribute",
            "connected_content",
            "data_extension_lookup",
            "nested_object",
            "content_block",
        ],
    },
    "conditional_complexity": {
        "description": "Complexity of conditional logic required",
        "values": [
            "simple_if_else",
            "nested_conditional",
            "loop_iteration",
            "multi_condition_chain",
            "filter_chain",
        ],
    },
    "fallback_challenge": {
        "description": "Type of fallback/edge case handling needed",
        "values": [
            "simple_default",
            "section_hiding",
            "conditional_fallback",
            "null_handling",
            "empty_array",
            "type_mismatch",
        ],
    },
}

# ---------------------------------------------------------------------------
# Code Reviewer Agent Dimensions
# ---------------------------------------------------------------------------
CODE_REVIEWER_DIMENSIONS = {
    "issue_category": {
        "description": "Category of code issue present in the email HTML",
        "values": [
            "redundant_inline_styles",
            "unused_css_class",
            "dead_mso_conditional",
            "unsupported_css_property",
            "invalid_nesting",
            "gmail_clip_risk",
            "base64_embedded_image",
            "excessive_table_depth",
            "mixed_issues",
            "anti_pattern",
            "spam_trigger",
            "malformed_link",
            "deprecated_html",
        ],
    },
    "html_complexity": {
        "description": "Structural complexity of the email HTML being reviewed",
        "values": [
            "simple_single_column",
            "multi_column_tables",
            "heavy_mso_conditionals",
            "vml_elements_present",
            "mixed_layout",
            "production_template",
            "dark_mode_optimised",
            "multi_esp_personalised",
        ],
    },
    "expected_severity": {
        "description": "Expected severity level of the most significant issue",
        "values": [
            "critical_only",
            "warning_dominant",
            "info_only",
            "mixed_severity",
            "clean_no_issues",
        ],
    },
    "file_size_scenario": {
        "description": "File size challenge in the email HTML",
        "values": [
            "under_60kb",
            "near_threshold_80kb",
            "over_102kb_clipping",
            "bloated_base64",
            "minimal",
        ],
    },
    "agent_routing": {
        "description": "Which specialist agents should be tagged for issues",
        "values": [
            "code_reviewer_only",
            "outlook_fixer_tagged",
            "dark_mode_tagged",
            "accessibility_tagged",
            "multi_agent_tagged",
        ],
    },
}

# ---------------------------------------------------------------------------
# Knowledge Agent Dimensions
# ---------------------------------------------------------------------------
KNOWLEDGE_DIMENSIONS = {
    "query_type": {
        "description": "Type of email development question asked",
        "values": [
            "css_property_support",
            "best_practice_lookup",
            "client_quirk_diagnosis",
            "comparison_query",
            "how_to_with_code",
            "troubleshooting",
        ],
    },
    "domain_coverage": {
        "description": "Which knowledge domains the answer requires",
        "values": [
            "single_domain_css",
            "single_domain_practice",
            "single_domain_quirks",
            "cross_domain",
        ],
    },
    "answer_complexity": {
        "description": "Expected depth and format of the answer",
        "values": [
            "yes_no_with_caveat",
            "explanation_with_code",
            "multi_client_matrix",
            "deep_troubleshooting",
        ],
    },
    "source_availability": {
        "description": "How well the knowledge base covers this question",
        "values": [
            "direct_match",
            "partial_coverage",
            "edge_case",
        ],
    },
}

# ---------------------------------------------------------------------------
# Innovation Agent Dimensions
# ---------------------------------------------------------------------------
INNOVATION_DIMENSIONS = {
    "technique_category": {
        "description": "Type of experimental email technique being prototyped",
        "values": [
            "css_checkbox_interactive",
            "css_animation_transition",
            "amp_for_email",
            "progressive_enhancement",
            "accessibility_innovation",
        ],
    },
    "client_coverage_challenge": {
        "description": "How widely the technique is supported across email clients",
        "values": [
            "broad_support",
            "modern_only",
            "single_engine",
            "near_zero_support",
        ],
    },
    "fallback_complexity": {
        "description": "Difficulty of providing a graceful fallback",
        "values": [
            "simple_static",
            "degraded_but_functional",
            "requires_conditional",
            "no_graceful_fallback",
        ],
    },
    "implementation_risk": {
        "description": "Risk level based on technique maturity and edge cases",
        "values": [
            "production_proven",
            "tested_limited",
            "experimental_untested",
            "bleeding_edge",
        ],
    },
}
