"""Adversarial test case generator and YAML loader.

Generates hostile inputs across 7 attack types for all 9 agents.
Cases are either generated programmatically or loaded from YAML fixtures.
Used by runner.py via --include-adversarial flag.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.ai.agents.evals.schemas import AdversarialCase
from app.core.logging import get_logger

logger = get_logger(__name__)

_YAML_DIR = Path(__file__).parent / "test_cases" / "adversarial"

# Agents that accept HTML input (html_input / brief with HTML expectations)
HTML_AGENTS: frozenset[str] = frozenset(
    {
        "scaffolder",
        "dark_mode",
        "outlook_fixer",
        "accessibility",
        "personalisation",
        "code_reviewer",
    }
)

ALL_AGENTS: tuple[str, ...] = (
    "scaffolder",
    "dark_mode",
    "content",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "knowledge",
    "innovation",
)

# Which attack types apply to which agent groups
_ALL_AGENTS_SET: frozenset[str] = frozenset(ALL_AGENTS)

_AGENT_ATTACK_MAP: dict[str, frozenset[str]] = {
    "long_string": _ALL_AGENTS_SET,
    "rtl_injection": _ALL_AGENTS_SET - frozenset({"innovation"}),
    "nested_conditionals": frozenset(
        {
            "personalisation",
            "outlook_fixer",
            "scaffolder",
            "dark_mode",
            "accessibility",
            "code_reviewer",
        }
    ),
    "missing_assets": HTML_AGENTS,
    "extreme_width": HTML_AGENTS | frozenset({"innovation"}),
    "emoji_heavy": _ALL_AGENTS_SET - frozenset({"innovation"}),
    "malformed_html": HTML_AGENTS,
}


def generate_adversarial_cases(agent: str) -> list[AdversarialCase]:
    """Generate programmatic adversarial test cases for an agent."""
    if agent not in ALL_AGENTS:
        msg = f"Unknown agent: {agent}"
        raise ValueError(msg)

    cases: list[AdversarialCase] = []
    generators = [
        ("long_string", _long_string_cases),
        ("rtl_injection", _rtl_injection_cases),
        ("nested_conditionals", _nested_conditional_cases),
        ("missing_assets", _missing_asset_cases),
        ("extreme_width", _extreme_dimension_cases),
        ("emoji_heavy", _emoji_cases),
        ("malformed_html", _malformed_html_cases),
    ]

    for attack_type, gen_fn in generators:
        if agent in _AGENT_ATTACK_MAP.get(attack_type, frozenset()):
            cases.extend(gen_fn(agent))

    return cases


def load_yaml_cases(agent: str) -> list[AdversarialCase]:
    """Load adversarial cases from YAML fixture file for an agent."""
    yaml_path = _YAML_DIR / f"{agent}.yaml"
    if not yaml_path.exists():
        return []

    with yaml_path.open() as f:
        raw: list[dict[str, Any]] = yaml.safe_load(f) or []

    cases: list[AdversarialCase] = []
    for entry in raw:
        cases.append(
            AdversarialCase(
                name=entry["name"],
                agent=agent,
                attack_type=entry["attack_type"],
                input_html=entry.get("input_html", ""),
                description=entry.get("description", ""),
                expected_behavior=entry.get("expected_behavior", ""),
            )
        )
    return cases


def get_all_cases(agent: str) -> list[AdversarialCase]:
    """Merge generated + YAML cases, deduplicate by name."""
    generated = generate_adversarial_cases(agent)
    from_yaml = load_yaml_cases(agent)

    seen: set[str] = set()
    merged: list[AdversarialCase] = []
    for case in [*generated, *from_yaml]:
        if case.name not in seen:
            seen.add(case.name)
            merged.append(case)

    return merged


def adversarial_to_runner_dict(case: AdversarialCase) -> dict[str, Any]:
    """Convert an AdversarialCase to the runner dict format expected by run_agent()."""
    agent = case.agent

    # Determine the correct input key for the agent
    if agent == "scaffolder":
        input_key = "brief"
    elif agent == "knowledge":
        input_key = "question"
    elif agent == "innovation":
        input_key = "technique"
    elif agent == "content":
        input_key = "text"
    else:
        input_key = "html_input"

    result: dict[str, Any] = {
        "id": f"adv-{case.name}",
        "dimensions": {"attack_type": case.attack_type, "adversarial": True},
        input_key: case.input_html,
        "expected_challenges": [case.expected_behavior] if case.expected_behavior else [],
    }

    # Add required extra fields for specific agents
    if agent == "content":
        result["operation"] = "rewrite"
        result["tone"] = None
        result["brand_voice"] = None
        result["num_alternatives"] = 1
    elif agent == "personalisation":
        result["platform"] = "braze"
        result["requirements"] = "Add dynamic personalisation"
    elif agent == "code_reviewer":
        result["focus"] = "all"
    elif agent == "knowledge":
        result["domain"] = None
    elif agent == "innovation":
        result["category"] = "interactive"

    return result


# ---------------------------------------------------------------------------
# Generator functions — each produces 2 cases per applicable agent
# ---------------------------------------------------------------------------


def _long_string_cases(agent: str) -> list[AdversarialCase]:
    long_heading = "A" * 500
    long_paragraph = "Word " * 2000  # ~10KB

    if agent == "scaffolder":
        return [
            AdversarialCase(
                name=f"{agent}_long_heading",
                agent=agent,
                attack_type="long_string",
                input_html=f"Create an email with heading: {long_heading}",
                description="500-char heading in brief",
                expected_behavior="Heading truncated or wrapped, no layout break",
            ),
            AdversarialCase(
                name=f"{agent}_long_paragraph",
                agent=agent,
                attack_type="long_string",
                input_html=f"Create an email with body: {long_paragraph}",
                description="10KB paragraph in brief",
                expected_behavior="Content rendered without overflow or timeout",
            ),
        ]

    if agent == "knowledge":
        return [
            AdversarialCase(
                name=f"{agent}_long_question",
                agent=agent,
                attack_type="long_string",
                input_html=f"What is the best practice for {long_heading} in email?",
                description="500-char question",
                expected_behavior="Answer focuses on core query, ignores padding",
            ),
            AdversarialCase(
                name=f"{agent}_long_context",
                agent=agent,
                attack_type="long_string",
                input_html=f"Given this context: {long_paragraph} — what CSS should I use?",
                description="10KB context in question",
                expected_behavior="Extracts relevant question, provides focused answer",
            ),
        ]

    if agent == "content":
        return [
            AdversarialCase(
                name=f"{agent}_long_input_text",
                agent=agent,
                attack_type="long_string",
                input_html=long_paragraph,
                description="10KB text to rewrite",
                expected_behavior="Processes or truncates gracefully, no timeout",
            ),
            AdversarialCase(
                name=f"{agent}_long_subject",
                agent=agent,
                attack_type="long_string",
                input_html=f"Subject: {long_heading}",
                description="500-char subject line input",
                expected_behavior="Shortens to reasonable length",
            ),
        ]

    if agent == "innovation":
        return [
            AdversarialCase(
                name=f"{agent}_long_technique",
                agent=agent,
                attack_type="long_string",
                input_html=f"Create a technique for {long_heading}",
                description="500-char technique description",
                expected_behavior="Extracts core technique, provides focused prototype",
            ),
            AdversarialCase(
                name=f"{agent}_long_requirements",
                agent=agent,
                attack_type="long_string",
                input_html=f"Build an interactive email that does: {long_paragraph}",
                description="10KB requirements",
                expected_behavior="Focuses on feasible subset, no timeout",
            ),
        ]

    # HTML agents (dark_mode, outlook_fixer, accessibility, personalisation, code_reviewer)
    long_html = (
        '<table role="presentation" width="600"><tr><td>'
        f"<h1>{long_heading}</h1>"
        f'<p style="margin:0 0 10px 0;">{long_paragraph}</p>'
        "</td></tr></table>"
    )
    return [
        AdversarialCase(
            name=f"{agent}_long_heading",
            agent=agent,
            attack_type="long_string",
            input_html=long_html,
            description="500-char heading + 10KB paragraph in HTML",
            expected_behavior="Processes HTML without layout break or timeout",
        ),
        AdversarialCase(
            name=f"{agent}_long_alt_text",
            agent=agent,
            attack_type="long_string",
            input_html=(
                '<table role="presentation" width="600"><tr><td>'
                f'<img src="https://example.com/img.png" alt="{long_heading}" width="600">'
                "</td></tr></table>"
            ),
            description="500-char alt text on image",
            expected_behavior="Preserves or truncates alt text, no crash",
        ),
    ]


def _rtl_injection_cases(agent: str) -> list[AdversarialCase]:
    rtl_mixed = (
        '<table role="presentation" width="600"><tr><td>'
        '<h1 style="margin:0;">Welcome \u0645\u0631\u062d\u0628\u0627 to our \u05e9\u05dc\u05d5\u05dd Sale!</h1>'
        '<p style="margin:0 0 10px 0;">\u0647\u0630\u0627 \u0646\u0635 \u0639\u0631\u0628\u064a mixed with English and \u05e2\u05d1\u05e8\u05d9\u05ea content.</p>'
        "</td></tr></table>"
    )
    rtl_only = (
        '<table role="presentation" width="600"><tr><td dir="rtl">'
        '<h1 style="margin:0;">\u0645\u0631\u062d\u0628\u0627 \u0628\u0643\u0645 \u0641\u064a \u0645\u062a\u062c\u0631\u0646\u0627</h1>'
        '<p style="margin:0 0 10px 0;">\u0627\u0633\u062a\u0645\u062a\u0639 \u0628\u0623\u0641\u0636\u0644 \u0627\u0644\u0639\u0631\u0648\u0636 \u0648\u0627\u0644\u062a\u062e\u0641\u064a\u0636\u0627\u062a</p>'
        "</td></tr></table>"
    )

    if agent == "scaffolder":
        return [
            AdversarialCase(
                name=f"{agent}_rtl_mixed_brief",
                agent=agent,
                attack_type="rtl_injection",
                input_html="Create a bilingual email: Welcome \u0645\u0631\u062d\u0628\u0627 — mix Arabic and English in heading and body.",
                description="RTL/LTR mixed brief",
                expected_behavior="Generates valid HTML with dir attributes, no broken layout",
            ),
        ]

    if agent == "knowledge":
        return [
            AdversarialCase(
                name=f"{agent}_rtl_question",
                agent=agent,
                attack_type="rtl_injection",
                input_html="How do I handle \u0645\u062d\u062a\u0648\u0649 \u0639\u0631\u0628\u064a in email templates with \u05e2\u05d1\u05e8\u05d9\u05ea fallback?",
                description="RTL characters in question",
                expected_behavior="Answers about bidi support, no encoding errors",
            ),
        ]

    if agent == "content":
        return [
            AdversarialCase(
                name=f"{agent}_rtl_mixed_text",
                agent=agent,
                attack_type="rtl_injection",
                input_html="Rewrite this: Welcome \u0645\u0631\u062d\u0628\u0627 to our \u05e9\u05dc\u05d5\u05dd mega sale event!",
                description="RTL/LTR mixed content text",
                expected_behavior="Preserves bidi text, no character corruption",
            ),
        ]

    # HTML agents
    return [
        AdversarialCase(
            name=f"{agent}_rtl_mixed",
            agent=agent,
            attack_type="rtl_injection",
            input_html=rtl_mixed,
            description="Arabic + Hebrew mixed with LTR in HTML",
            expected_behavior="Preserves bidi content, adds dir attributes if needed",
        ),
        AdversarialCase(
            name=f"{agent}_rtl_full",
            agent=agent,
            attack_type="rtl_injection",
            input_html=rtl_only,
            description="Full RTL Arabic email",
            expected_behavior="Preserves dir=rtl, no layout inversion bugs",
        ),
    ]


def _nested_conditional_cases(agent: str) -> list[AdversarialCase]:
    # 5-level Liquid nesting
    liquid_nested = (
        '<table role="presentation" width="600"><tr><td>'
        "{% if user.vip %}"
        "{% if user.locale == 'en' %}"
        "{% if user.age > 18 %}"
        "{% if user.opted_in %}"
        "{% if user.segment == 'premium' %}"
        '<p style="margin:0;">VIP Premium English Adult Opted-in Content</p>'
        "{% else %}"
        '<p style="margin:0;">VIP Standard Content</p>'
        "{% endif %}"
        "{% endif %}"
        "{% endif %}"
        "{% endif %}"
        "{% endif %}"
        "</td></tr></table>"
    )

    # 5-level AMPscript nesting
    ampscript_nested = (
        '<table role="presentation" width="600"><tr><td>'
        "%%[IF @vip == 'true' THEN]%%"
        "%%[IF @locale == 'en' THEN]%%"
        "%%[IF @age > 18 THEN]%%"
        "%%[IF @opted_in == 'true' THEN]%%"
        "%%[IF @segment == 'premium' THEN]%%"
        '<p style="margin:0;">VIP Premium Content</p>'
        "%%[ELSE]%%"
        '<p style="margin:0;">Standard Content</p>'
        "%%[ENDIF]%%"
        "%%[ENDIF]%%"
        "%%[ENDIF]%%"
        "%%[ENDIF]%%"
        "%%[ENDIF]%%"
        "</td></tr></table>"
    )

    return [
        AdversarialCase(
            name=f"{agent}_liquid_5level",
            agent=agent,
            attack_type="nested_conditionals",
            input_html=liquid_nested,
            description="5-level nested Liquid conditionals",
            expected_behavior="Preserves conditional structure, no parsing errors",
        ),
        AdversarialCase(
            name=f"{agent}_ampscript_5level",
            agent=agent,
            attack_type="nested_conditionals",
            input_html=ampscript_nested,
            description="5-level nested AMPscript conditionals",
            expected_behavior="Preserves AMPscript blocks, no stripping or corruption",
        ),
    ]


def _missing_asset_cases(agent: str) -> list[AdversarialCase]:
    broken_images = (
        '<table role="presentation" width="600">'
        "<tr><td>"
        '<img src="" alt="Hero" width="600">'
        '<img src="https://broken.invalid/404.png" alt="Banner" width="600">'
        '<img alt="No src at all" width="300">'
        "</td></tr>"
        "</table>"
    )
    missing_fonts = (
        '<table role="presentation" width="600"><tr><td>'
        "<p style=\"margin:0 0 10px 0;font-family:'NonExistentFont','AnotherMissing',sans-serif;\">"
        "Content with missing font stack"
        "</p>"
        "</td></tr></table>"
    )

    return [
        AdversarialCase(
            name=f"{agent}_broken_images",
            agent=agent,
            attack_type="missing_assets",
            input_html=broken_images,
            description="Empty src, 404 URL, and missing src attribute on images",
            expected_behavior="Handles gracefully, preserves alt text, no crash",
        ),
        AdversarialCase(
            name=f"{agent}_missing_fonts",
            agent=agent,
            attack_type="missing_assets",
            input_html=missing_fonts,
            description="Font-family references to nonexistent fonts",
            expected_behavior="Falls back to generic family, no rendering error",
        ),
    ]


def _extreme_dimension_cases(agent: str) -> list[AdversarialCase]:
    narrow = (
        '<table role="presentation" width="200"><tr><td>'
        '<h1 style="margin:0;font-size:24px;">Narrow Viewport Email</h1>'
        '<p style="margin:0 0 10px 0;">This email must render at 200px width.</p>'
        '<table role="presentation" width="100%"><tr>'
        '<td width="50%">Col 1</td><td width="50%">Col 2</td>'
        "</tr></table>"
        "</td></tr></table>"
    )
    ultra_wide = (
        '<table role="presentation" width="1200"><tr><td>'
        '<h1 style="margin:0;font-size:48px;">Ultra-Wide Email at 1200px</h1>'
        '<p style="margin:0 0 10px 0;">Testing extreme width handling.</p>'
        '<table role="presentation" width="100%"><tr>'
        '<td width="25%">A</td><td width="25%">B</td>'
        '<td width="25%">C</td><td width="25%">D</td>'
        "</tr></table>"
        "</td></tr></table>"
    )

    if agent == "scaffolder":
        return [
            AdversarialCase(
                name=f"{agent}_narrow_200px",
                agent=agent,
                attack_type="extreme_width",
                input_html="Create a 2-column email that must work at 200px viewport width",
                description="200px viewport brief",
                expected_behavior="Single-column fallback or responsive stacking",
            ),
            AdversarialCase(
                name=f"{agent}_ultrawide_1200px",
                agent=agent,
                attack_type="extreme_width",
                input_html="Create a 4-column dashboard email for 1200px desktop displays",
                description="1200px ultra-wide brief",
                expected_behavior="Constrains to max-width, no horizontal overflow",
            ),
        ]

    if agent == "innovation":
        return [
            AdversarialCase(
                name=f"{agent}_narrow_interactive",
                agent=agent,
                attack_type="extreme_width",
                input_html="Create an interactive tabbed section that works at 200px mobile width",
                description="Interactive element at extreme narrow width",
                expected_behavior="Graceful degradation, tabs stack vertically",
            ),
            AdversarialCase(
                name=f"{agent}_ultrawide_animation",
                agent=agent,
                attack_type="extreme_width",
                input_html="Create a CSS animation banner spanning 1200px",
                description="Animation at ultra-wide width",
                expected_behavior="Animation contained within bounds",
            ),
        ]

    # HTML agents
    return [
        AdversarialCase(
            name=f"{agent}_narrow_200px",
            agent=agent,
            attack_type="extreme_width",
            input_html=narrow,
            description="200px viewport width email HTML",
            expected_behavior="Processes without breaking, columns may stack",
        ),
        AdversarialCase(
            name=f"{agent}_ultrawide_1200px",
            agent=agent,
            attack_type="extreme_width",
            input_html=ultra_wide,
            description="1200px ultra-wide email HTML",
            expected_behavior="Processes without breaking layout constraints",
        ),
    ]


def _emoji_cases(agent: str) -> list[AdversarialCase]:
    emoji_html = (
        '<table role="presentation" width="600"><tr><td>'
        '<h1 style="margin:0;">\U0001f525\U0001f389 MEGA SALE \U0001f4a5\U0001f6d2</h1>'
        '<p style="margin:0 0 10px 0;">Get \U0001f4b0 50% off \U0001f381 gifts!</p>'
        '<a href="https://example.com" style="color:#0066cc;">'
        "\U0001f449 Shop Now \U0001f6d2\U0001f4a8</a>"
        "</td></tr></table>"
    )
    emoji_alt = (
        '<table role="presentation" width="600"><tr><td>'
        '<img src="https://example.com/hero.png" alt="\U0001f525 Hot Deal \U0001f525" width="600">'
        "</td></tr></table>"
    )

    if agent == "scaffolder":
        return [
            AdversarialCase(
                name=f"{agent}_emoji_brief",
                agent=agent,
                attack_type="emoji_heavy",
                input_html="Create a \U0001f525\U0001f389 MEGA SALE email with \U0001f6d2 shopping CTAs and \U0001f4b0 price badges",
                description="Emoji-heavy brief",
                expected_behavior="Generates valid HTML, emoji in text nodes only",
            ),
        ]

    if agent == "content":
        return [
            AdversarialCase(
                name=f"{agent}_emoji_subject",
                agent=agent,
                attack_type="emoji_heavy",
                input_html="\U0001f525\U0001f389 MEGA SALE \U0001f4a5 50% OFF \U0001f6d2 Shop Now \U0001f4b0\U0001f381\U0001f38a",
                description="Emoji-saturated subject line",
                expected_behavior="Reduces emoji count, preserves meaning",
            ),
        ]

    if agent == "knowledge":
        return [
            AdversarialCase(
                name=f"{agent}_emoji_question",
                agent=agent,
                attack_type="emoji_heavy",
                input_html="Do emoji \U0001f525\U0001f389\U0001f4a5 in subject lines \U0001f4e7 hurt deliverability \U0001f4c9?",
                description="Emoji-laden question",
                expected_behavior="Parses question correctly, answers about emoji impact",
            ),
        ]

    # HTML agents
    return [
        AdversarialCase(
            name=f"{agent}_emoji_heavy",
            agent=agent,
            attack_type="emoji_heavy",
            input_html=emoji_html,
            description="Emoji in headings, body, and CTA links",
            expected_behavior="Preserves emoji in text, no encoding errors",
        ),
        AdversarialCase(
            name=f"{agent}_emoji_alt_text",
            agent=agent,
            attack_type="emoji_heavy",
            input_html=emoji_alt,
            description="Emoji in image alt text",
            expected_behavior="Preserves or sanitizes emoji in alt attribute",
        ),
    ]


def _malformed_html_cases(agent: str) -> list[AdversarialCase]:
    unclosed_table = (
        '<table role="presentation" width="600"><tr><td>'
        '<table role="presentation" width="100%"><tr><td>'
        '<p style="margin:0;">Nested table never closed</p>'
        "</td></tr>"
        # Missing </table> intentionally
        "</td></tr></table>"
    )
    nested_links = (
        '<table role="presentation" width="600"><tr><td>'
        '<a href="https://outer.com">'
        "Outer link "
        '<a href="https://inner.com">Inner link</a>'
        " more outer"
        "</a>"
        "</td></tr></table>"
    )
    return [
        AdversarialCase(
            name=f"{agent}_unclosed_table",
            agent=agent,
            attack_type="malformed_html",
            input_html=unclosed_table,
            description="Nested table with missing closing tag",
            expected_behavior="Handles gracefully, fixes or reports the issue",
        ),
        AdversarialCase(
            name=f"{agent}_nested_links",
            agent=agent,
            attack_type="malformed_html",
            input_html=nested_links,
            description="Illegal nested <a> inside <a>",
            expected_behavior="Flattens or reports invalid nesting",
        ),
    ]
