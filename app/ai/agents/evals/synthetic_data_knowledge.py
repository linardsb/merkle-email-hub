"""Synthetic test data for the Knowledge agent evaluation.

10 dimension-based test cases covering CSS property support, best practices,
client quirks, comparison queries, and troubleshooting scenarios.
"""

from typing import Any

KNOWLEDGE_TEST_CASES: list[dict[str, Any]] = [
    # --- CSS Property Support ---
    {
        "id": "kn-001",
        "question": "Does Gmail support the CSS display:flex property in emails?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "yes_no_with_caveat",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Correctly state that Gmail does NOT support display:flex",
            "Mention table-based layout as the standard alternative",
            "Cite css_support domain document",
            "High confidence (well-documented topic)",
        ],
    },
    {
        "id": "kn-002",
        "question": "Which email clients support CSS border-radius?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "multi_client_matrix",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "List supported clients (Apple Mail, iOS, most modern webmail)",
            "Note Outlook Windows does NOT support border-radius",
            "Mention progressive enhancement approach",
            "Cite Can I Email data",
        ],
    },
    # --- Best Practice ---
    {
        "id": "kn-003",
        "question": "What is the recommended approach for responsive email images?",
        "domain": "best_practices",
        "dimensions": {
            "query_type": "best_practice_lookup",
            "domain_coverage": "single_domain_practice",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Include explicit width/height attributes",
            "Use style='display:block; width:100%; height:auto;'",
            "Mention max-width for fluid layouts",
            "Provide HTML code example with img tag",
            "Cite best_practices document",
        ],
    },
    {
        "id": "kn-004",
        "question": "How do I create a bulletproof button for email?",
        "domain": None,
        "dimensions": {
            "query_type": "how_to_with_code",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Provide VML-based bulletproof button code for Outlook",
            "Include padding-based CSS fallback for modern clients",
            "Show MSO conditional comment wrapping",
            "Code must use placeholder URLs only",
        ],
    },
    # --- Client Quirks ---
    {
        "id": "kn-005",
        "question": "Why does Outlook add extra spacing to my email tables?",
        "domain": "client_quirks",
        "dimensions": {
            "query_type": "client_quirk_diagnosis",
            "domain_coverage": "single_domain_quirks",
            "answer_complexity": "deep_troubleshooting",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain Word rendering engine table handling",
            "Mention cellpadding/cellspacing/border='0' attributes",
            "Reference mso-table-lspace/rspace CSS properties",
            "Cite Outlook quirks document",
        ],
    },
    {
        "id": "kn-006",
        "question": "How does Gmail handle dark mode in emails?",
        "domain": None,
        "dimensions": {
            "query_type": "client_quirk_diagnosis",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain Gmail's auto-inversion behavior",
            "Mention color-scheme meta tag",
            "Distinguish Gmail web vs Android vs iOS behavior",
            "Reference both dark_mode css_support and client_quirks docs",
        ],
    },
    # --- Comparison ---
    {
        "id": "kn-007",
        "question": "Compare Outlook's and Apple Mail's CSS support for email development",
        "domain": None,
        "dimensions": {
            "query_type": "comparison_query",
            "domain_coverage": "cross_domain",
            "answer_complexity": "multi_client_matrix",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Contrast Word rendering engine (Outlook) vs WebKit (Apple Mail)",
            "List key CSS properties where they differ",
            "Note Apple Mail is most permissive, Outlook most restrictive",
            "Cite multiple source documents",
        ],
    },
    # --- Troubleshooting ---
    {
        "id": "kn-008",
        "question": "My email is getting clipped in Gmail. How do I fix it?",
        "domain": None,
        "dimensions": {
            "query_type": "troubleshooting",
            "domain_coverage": "cross_domain",
            "answer_complexity": "deep_troubleshooting",
            "source_availability": "direct_match",
        },
        "expected_challenges": [
            "Explain the 102KB Gmail clipping threshold",
            "Suggest file size reduction strategies",
            "Mention inlining CSS, removing comments, minifying",
            "Reference file_size best practice document",
        ],
    },
    # --- Edge Cases ---
    {
        "id": "kn-009",
        "question": "Does Samsung Mail support CSS animations in emails?",
        "domain": "css_support",
        "dimensions": {
            "query_type": "css_property_support",
            "domain_coverage": "single_domain_css",
            "answer_complexity": "yes_no_with_caveat",
            "source_availability": "edge_case",
        },
        "expected_challenges": [
            "Acknowledge limited data on Samsung Mail animation support",
            "Low confidence due to sparse knowledge base coverage",
            "Suggest progressive enhancement regardless",
            "Should NOT fabricate specific version support claims",
        ],
    },
    {
        "id": "kn-010",
        "question": "What is the best email client for testing responsive emails?",
        "domain": None,
        "dimensions": {
            "query_type": "best_practice_lookup",
            "domain_coverage": "cross_domain",
            "answer_complexity": "explanation_with_code",
            "source_availability": "partial_coverage",
        },
        "expected_challenges": [
            "Recommend testing across rendering engines (WebKit, Word, Blink)",
            "Suggest specific clients per engine",
            "Medium confidence (opinion-based, partially covered)",
            "Should NOT present opinion as authoritative fact",
        ],
    },
]
