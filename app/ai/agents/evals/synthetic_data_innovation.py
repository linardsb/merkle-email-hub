"""Synthetic test data for the Innovation agent evaluation.

10 dimension-based test cases covering CSS checkbox hacks, AMP for Email,
CSS animations, progressive enhancement, and accessibility innovations.
"""

from typing import Any

INNOVATION_TEST_CASES: list[dict[str, Any]] = [
    # --- CSS Checkbox Interactive ---
    {
        "id": "inn-001",
        "technique": "Create a CSS-only tabbed content section for email where users can click tabs to show/hide different product categories without JavaScript.",
        "category": "interactive",
        "dimensions": {
            "technique_category": "css_checkbox_interactive",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use hidden checkbox + label + sibling selector pattern",
            "Provide static fallback showing all content stacked",
            "Note Apple Mail, iOS Mail support; Outlook/Gmail do NOT",
            "Coverage should be ~40-50% (WebKit clients only)",
        ],
    },
    {
        "id": "inn-002",
        "technique": "Build a CSS-only accordion FAQ section for email. Each question should expand/collapse when clicked.",
        "category": "interactive",
        "dimensions": {
            "technique_category": "css_checkbox_interactive",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "degraded_but_functional",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use radio input + label pattern for mutual exclusion",
            "Fallback: all answers visible (stacked)",
            "Correct client coverage estimate (Apple Mail yes, Gmail no)",
            "Note file size impact of repeated checkbox patterns",
        ],
    },
    # --- CSS Animations ---
    {
        "id": "inn-003",
        "technique": "Add a subtle fade-in animation to the hero image and CTA button when the email is opened.",
        "category": "visual_effects",
        "dimensions": {
            "technique_category": "css_animation_transition",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use @keyframes with opacity transition",
            "Fallback: elements visible immediately (no animation)",
            "Note Apple Mail supports, Outlook/Gmail strip @keyframes",
            "Reduced motion media query for accessibility",
        ],
    },
    {
        "id": "inn-004",
        "technique": "Create a countdown timer animation in CSS that counts down from 10 to 0 for a flash sale email.",
        "category": "visual_effects",
        "dimensions": {
            "technique_category": "css_animation_transition",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "experimental_untested",
        },
        "expected_challenges": [
            "Acknowledge CSS-only countdown has severe limitations",
            "High risk / avoid recommendation (timing unreliable)",
            "Suggest server-side image countdown as better alternative",
            "Very low coverage (~20% at best)",
        ],
    },
    # --- AMP for Email ---
    {
        "id": "inn-005",
        "technique": "Build an interactive product carousel using AMP for Email that users can swipe through directly in their inbox.",
        "category": "amp",
        "dimensions": {
            "technique_category": "amp_for_email",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use amp-carousel component with proper AMP boilerplate",
            "MIME multipart fallback (HTML version for non-AMP clients)",
            "Coverage: Gmail only (~30%), must be sender-verified",
            "Note AMP sender registration requirement",
        ],
    },
    {
        "id": "inn-006",
        "technique": "Create an in-email survey form using AMP for Email where users can submit responses without leaving the inbox.",
        "category": "amp",
        "dimensions": {
            "technique_category": "amp_for_email",
            "client_coverage_challenge": "single_engine",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Use amp-form with proper action-xhr endpoint",
            "Fallback: link to external survey form",
            "Note CORS requirements for AMP form endpoints",
            "Gmail-only coverage, sender registration needed",
        ],
    },
    # --- Progressive Enhancement ---
    {
        "id": "inn-007",
        "technique": "Use CSS Grid for a product grid layout that falls back to table-based layout for Outlook.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "broad_support",
            "fallback_complexity": "requires_conditional",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "CSS Grid in style block for modern clients",
            "MSO conditional table-based fallback for Outlook",
            "Coverage: ~70% see Grid, 30% see table fallback",
            "Both versions must look professional",
        ],
    },
    {
        "id": "inn-008",
        "technique": "Implement CSS custom properties (variables) for theming an email with a single color change point.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "degraded_but_functional",
            "implementation_risk": "tested_limited",
        },
        "expected_challenges": [
            "Define --brand-color in style block",
            "Inline style fallback values for Outlook/Gmail",
            "Note Gmail strips custom properties",
            "Coverage ~45% (Apple Mail, iOS yes; Gmail, Outlook no)",
        ],
    },
    # --- Accessibility Innovation ---
    {
        "id": "inn-009",
        "technique": "Add prefers-reduced-motion support to all animations in an email, with a static fallback for users who prefer reduced motion.",
        "category": "accessibility",
        "dimensions": {
            "technique_category": "accessibility_innovation",
            "client_coverage_challenge": "modern_only",
            "fallback_complexity": "simple_static",
            "implementation_risk": "production_proven",
        },
        "expected_challenges": [
            "Use @media (prefers-reduced-motion: reduce) query",
            "Disable all animations and transitions inside the query",
            "Note: only clients that support @media support this",
            "Recommend as best practice alongside any animation technique",
        ],
    },
    # --- Edge Case / Near-Zero Support ---
    {
        "id": "inn-010",
        "technique": "Create an email with CSS Scroll Snap for a horizontal scrollable gallery of product images.",
        "category": "progressive_enhancement",
        "dimensions": {
            "technique_category": "progressive_enhancement",
            "client_coverage_challenge": "near_zero_support",
            "fallback_complexity": "no_graceful_fallback",
            "implementation_risk": "bleeding_edge",
        },
        "expected_challenges": [
            "Acknowledge scroll-snap has near-zero email client support",
            "Recommend 'avoid' — technique not viable for email",
            "Suggest alternative: linked image grid or AMP carousel",
            "Risk level should be 'high'",
        ],
    },
]
