"""Generate review data JSON for the streamlined eval review tool.

Only includes LLM-judged verdicts that need human review (208 rows).
Bundles trace HTML, brief, judge reasoning, and criterion metadata.

Usage:
    python scripts/generate-review-data.py --traces-dir traces/ --output docs/eval-review-data.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AGENTS = [
    "scaffolder",
    "dark_mode",
    "content",
    "outlook_fixer",
    "accessibility",
    "personalisation",
    "code_reviewer",
    "knowledge",
    "innovation",
]

CRITERION_INFO: dict[str, dict[str, str]] = {
    # Scaffolder
    "brief_fidelity": {
        "agent": "scaffolder",
        "title": "Brief Fidelity",
        "what": "Does the generated HTML faithfully implement all key elements from the brief?",
        "pass": "Layout type, sections, content areas, and specific requirements from brief are all present",
        "fail": "Missing requested sections, elements, or layout requirements from the brief",
        "tip": "Compare the brief requirements (shown above) with the HTML output. Check that each requested section exists.",
    },
    "email_layout_patterns": {
        "agent": "scaffolder",
        "title": "Email Layout Patterns",
        "what": "Does the HTML use email-appropriate layout patterns exclusively?",
        "pass": "Uses nested <table> with role='presentation'; no flexbox/grid/floats; width <= 600px",
        "fail": "Uses flexbox, CSS grid, float layouts, or other unsupported patterns",
        "tip": "Look for any <div> used for layout (columns, widths). Tables should be the only layout mechanism.",
    },
    "mso_conditional_correctness": {
        "agent": "scaffolder,outlook_fixer",
        "title": "MSO Conditional Correctness",
        "what": "Are MSO conditional comments present and correctly structured?",
        "pass": "Has <!--[if mso]> and <!--[if !mso]> blocks with proper closing; VML inside MSO conditionals",
        "fail": "Missing conditionals, improper nesting, unclosed blocks",
        "tip": "Search the HTML for '<!--[if' and check each has a matching '<![endif]-->'.",
    },
    "dark_mode_readiness": {
        "agent": "scaffolder",
        "title": "Dark Mode Readiness",
        "what": "Does output include dark mode support?",
        "pass": "Includes color-scheme meta tags, @media (prefers-color-scheme: dark) rules, and Outlook selectors",
        "fail": "Missing meta tags, media queries, or Outlook dark mode selectors",
        "tip": "Look for: meta color-scheme tag, @media prefers-color-scheme, [data-ogsc]/[data-ogsb] selectors.",
    },
    "accessibility_baseline": {
        "agent": "scaffolder",
        "title": "Accessibility Baseline",
        "what": "Does the HTML meet baseline accessibility standards?",
        "pass": "Has lang attribute, role='article' wrapper, role='presentation' on layout tables, meaningful alt text",
        "fail": "Missing lang, roles, alt text, or heading hierarchy issues",
        "tip": "Check: <html lang=...>, role attributes on tables, alt text on images.",
    },
    # Dark Mode
    "color_coherence": {
        "agent": "dark_mode",
        "title": "Color Coherence",
        "what": "Are dark mode colors visually coherent and not just technically present?",
        "pass": "Background colors are dark, text is light and readable; brand colors adjusted appropriately",
        "fail": "Colors inverted but not coherent; readability issues; white-on-light or dark-on-dark",
        "tip": "Preview the HTML — does the dark mode version look intentionally designed, not just mechanically inverted?",
    },
    "html_preservation": {
        "agent": "dark_mode,outlook_fixer,personalisation",
        "title": "HTML Preservation",
        "what": "Is the original HTML structure fully preserved after agent processing?",
        "pass": "No elements removed, no attributes deleted, no inline styles stripped; only additions allowed",
        "fail": "Elements removed, attributes deleted, inline styles stripped, or HTML modified",
        "tip": "Compare input vs output HTML. The agent should only ADD things, never remove or alter existing content.",
    },
    "outlook_selector_completeness": {
        "agent": "dark_mode",
        "title": "Outlook Selector Completeness",
        "what": "Are [data-ogsc] and [data-ogsb] selectors present for all dark mode color overrides?",
        "pass": "Every dark mode color change has corresponding Outlook attribute selectors",
        "fail": "Missing Outlook selectors for some color changes",
        "tip": "Each color in @media prefers-color-scheme should have a matching [data-ogsc] or [data-ogsb] rule.",
    },
    "meta_and_media_query": {
        "agent": "dark_mode",
        "title": "Meta & Media Query",
        "what": "Does output include necessary meta tags and media queries?",
        "pass": "Includes <meta name='color-scheme'> and @media (prefers-color-scheme: dark) with !important",
        "fail": "Missing meta tags or media queries for dark mode",
        "tip": "Search for 'color-scheme' in both meta tags and CSS.",
    },
    "contrast_preservation": {
        "agent": "dark_mode",
        "title": "Contrast Preservation",
        "what": "Do all text-background combinations maintain 4.5:1 contrast in dark mode?",
        "pass": "All text/background combinations achieve WCAG AA 4.5:1 contrast ratio",
        "fail": "Contrast falls below 4.5:1 for some combinations",
        "tip": "Look at light text on dark backgrounds — is there enough contrast? Check links too.",
    },
    # Content
    "copy_quality": {
        "agent": "content",
        "title": "Copy Quality",
        "what": "Is the generated copy compelling, clear, and well-crafted?",
        "pass": "Subject lines: 40-60 chars; CTAs: action verb, 2-5 words; body: scannable, short paragraphs",
        "fail": "Unclear writing, missing value, overly long/short, poor structure",
        "tip": "Read the output as an email recipient would. Is it compelling? Does it make sense?",
    },
    "tone_accuracy": {
        "agent": "content",
        "title": "Tone Accuracy",
        "what": "Does output match the requested tone?",
        "pass": "Tone matches requirements (professional/casual/urgent/luxury as requested)",
        "fail": "Tone mismatch — e.g., casual tone when professional was requested",
        "tip": "Check the brief for requested tone, then read the output. Does the voice match?",
    },
    "spam_avoidance": {
        "agent": "content",
        "title": "Spam Avoidance",
        "what": "Is output free of common email spam triggers?",
        "pass": "No ALL CAPS, excessive punctuation (!!!), or trigger phrases like 'click here', 'buy now'",
        "fail": "Contains spam trigger words, ALL CAPS, or excessive punctuation",
        "tip": "Scan for: ALL CAPS words, !!!, 'free', 'guaranteed', 'limited time', 'click here'.",
    },
    "operation_compliance": {
        "agent": "content",
        "title": "Operation Compliance",
        "what": "Does output correctly follow the requested operation type?",
        "pass": "Operation executed correctly (subject_line within limits, shorten = 30-50% reduction, etc.)",
        "fail": "Operation not correctly executed",
        "tip": "Check the operation type in the brief, then verify the output follows those constraints.",
    },
    "security_and_pii": {
        "agent": "content",
        "title": "Security & PII",
        "what": "Contains no real PII (names, emails, SSNs)?",
        "pass": "Uses placeholders like [NAME], [EMAIL]; plain text only; no HTML/JS",
        "fail": "Contains real names, emails, SSNs, phone numbers, or executable content",
        "tip": "Look for anything that looks like a real person's data. Placeholders are fine.",
    },
    # Outlook Fixer
    "vml_wellformedness": {
        "agent": "outlook_fixer",
        "title": "VML Well-formedness",
        "what": "Are VML elements properly structured?",
        "pass": "xmlns:v namespace present; all <v:*> elements properly closed; correct attributes",
        "fail": "Malformed VML, missing namespaces, improper attributes",
        "tip": "Search for '<v:' elements. Each should have proper closing and required attributes.",
    },
    "fix_completeness": {
        "agent": "outlook_fixer",
        "title": "Fix Completeness",
        "what": "Are all identified Outlook rendering issues addressed?",
        "pass": "Multi-column layouts have ghost tables; CSS backgrounds have VML fallback; all issues fixed",
        "fail": "Missing fixes or partial solutions",
        "tip": "Check expected_challenges — does the output address each one?",
    },
    "outlook_version_targeting": {
        "agent": "outlook_fixer",
        "title": "Outlook Version Targeting",
        "what": "Are fixes correctly scoped to affected Outlook versions?",
        "pass": "MSO conditionals target correct version range; non-MSO clients render correctly",
        "fail": "Incorrect version targeting or breaking non-Outlook clients",
        "tip": "Check <!--[if gte mso 9]> patterns. Are version ranges appropriate?",
    },
    # Accessibility
    "wcag_aa_compliance": {
        "agent": "accessibility",
        "title": "WCAG AA Compliance",
        "what": "Does output meet WCAG 2.1 AA standards for email?",
        "pass": "Has lang attribute, role='presentation' on layout tables, <title>, role='article' wrapper",
        "fail": "Missing any required WCAG elements",
        "tip": "Check for: lang=, role='presentation', <title> tag, charset meta.",
    },
    "alt_text_quality": {
        "agent": "accessibility",
        "title": "Alt Text Quality",
        "what": "Do all images have appropriate alt text?",
        "pass": "Informative images: descriptive alt; decorative: alt=''; max ~125 chars; no 'image of' prefix",
        "fail": "Missing alt, generic text like 'image' or 'photo', or 'image of...' prefix",
        "tip": "Find all <img> tags. Does each have an alt attribute? Is it meaningful?",
    },
    "contrast_ratio_accuracy": {
        "agent": "accessibility",
        "title": "Contrast Ratio Accuracy",
        "what": "Are color contrast issues identified and fixed?",
        "pass": "Normal text >= 4.5:1; large text >= 3:1 contrast ratio",
        "fail": "Low-contrast text introduced or not addressed",
        "tip": "Look at text colors vs background colors. Light gray text on white = fail.",
    },
    "semantic_structure": {
        "agent": "accessibility",
        "title": "Semantic Structure",
        "what": "Is heading hierarchy sequential with no skipped levels?",
        "pass": "At most one <h1>; headings h1->h2->h3 without gaps; descriptive link text",
        "fail": "Skipped heading levels, generic 'click here' link text",
        "tip": "Find all heading tags. Do they go in order? Find all links — is the text descriptive?",
    },
    "screen_reader_compatibility": {
        "agent": "accessibility",
        "title": "Screen Reader Compatibility",
        "what": "Is output compatible with major screen readers?",
        "pass": "Layout tables have role='presentation'; VML inside MSO conditionals; correct reading order",
        "fail": "VML exposed to screen readers, ARIA conflicts, content removed",
        "tip": "Check role attributes on tables, and that VML is inside MSO conditionals.",
    },
    # Personalisation
    "syntax_correctness": {
        "agent": "personalisation",
        "title": "Syntax Correctness",
        "what": "Is the ESP-specific syntax valid?",
        "pass": "All template tags properly opened/closed; correct case; no mixed platform syntax",
        "fail": "Malformed tags, mismatched delimiters, wrong function case, mixed syntax",
        "tip": "Check that all {{ }} or %%[ ]%% tags are properly balanced and platform-consistent.",
    },
    "fallback_completeness": {
        "agent": "personalisation",
        "title": "Fallback Completeness",
        "what": "Does every dynamic variable have a fallback/default value?",
        "pass": "Every variable has a fallback (default filter, IF/ELSE, ternary)",
        "fail": "Variables without any fallback mechanism",
        "tip": "Find each dynamic variable — does it have a | default: or IF/ELSE wrapper?",
    },
    "platform_accuracy": {
        "agent": "personalisation",
        "title": "Platform Accuracy",
        "what": "Is output using the correct ESP platform's syntax exclusively?",
        "pass": "Only uses the requested platform syntax (Braze=Liquid, SFMC=AMPscript, etc.)",
        "fail": "Mixed platform syntax or wrong platform used",
        "tip": "Check the brief for which ESP, then verify only that platform's syntax appears.",
    },
    "logic_match": {
        "agent": "personalisation",
        "title": "Logic Match",
        "what": "Does personalisation logic match the natural language requirements?",
        "pass": "Conditional logic matches stated intent; correct iteration constructs",
        "fail": "Logic doesn't match requirements or missing control structures",
        "tip": "Read the brief requirements, then check if the template logic implements them correctly.",
    },
    # Code Reviewer
    "issue_genuineness": {
        "agent": "code_reviewer",
        "title": "Issue Genuineness",
        "what": "Are all flagged issues real problems (no false positives)?",
        "pass": "Every issue is genuine; standard email patterns (table layouts, MSO, VML) NOT flagged",
        "fail": "Flags normal email HTML patterns as issues",
        "tip": "Are any flagged 'issues' actually standard email practices? Those are false positives.",
    },
    "suggestion_actionability": {
        "agent": "code_reviewer",
        "title": "Suggestion Actionability",
        "what": "Does every issue include a concrete, actionable fix?",
        "pass": "Suggestions specify exactly what to change (e.g., 'Replace flexbox with table layout')",
        "fail": "Generic advice like 'consider improving' without specifics",
        "tip": "For each issue, is the suggestion specific enough to act on immediately?",
    },
    "severity_accuracy": {
        "agent": "code_reviewer",
        "title": "Severity Accuracy",
        "what": "Is severity classification correct for each issue?",
        "pass": "Critical = breaks rendering; warning = degrades experience; info = optimisation",
        "fail": "Over/under-classifying severity",
        "tip": "Would this issue actually break email rendering (critical) or just be sub-optimal (info)?",
    },
    "coverage_completeness": {
        "agent": "code_reviewer",
        "title": "Coverage Completeness",
        "what": "Does review catch all significant issues in the HTML?",
        "pass": "Catches issues matching expected_challenges; missing info-level is acceptable",
        "fail": "Misses critical issues in the HTML",
        "tip": "Check expected_challenges — did the reviewer find the major problems?",
    },
    "output_format": {
        "agent": "code_reviewer",
        "title": "Output Format",
        "what": "Is output valid JSON with the expected structure?",
        "pass": "Contains 'issues' array with rule/severity/message fields, plus 'summary' string",
        "fail": "Invalid JSON or missing required fields",
        "tip": "Try parsing the output as JSON. Check for issues[] and summary fields.",
    },
    # Knowledge
    "answer_accuracy": {
        "agent": "knowledge",
        "title": "Answer Accuracy",
        "what": "Is the answer factually correct based on retrieved context?",
        "pass": "Claims about CSS support and email client behavior match source documents",
        "fail": "Incorrect facts or unsupported/hallucinated claims",
        "tip": "Cross-reference factual claims with the cited sources. Any made-up facts?",
    },
    "citation_grounding": {
        "agent": "knowledge",
        "title": "Citation Grounding",
        "what": "Does the answer cite specific source documents?",
        "pass": "Every factual claim references a source document",
        "fail": "Facts without citations or citations to non-existent documents",
        "tip": "Are claims backed by named sources? Or are they unsourced assertions?",
    },
    "code_example_quality": {
        "agent": "knowledge",
        "title": "Code Example Quality",
        "what": "Are code examples working and email-safe?",
        "pass": "Uses table-based layouts, inline styles, placeholder URLs; no <script> or JS",
        "fail": "Code with syntax errors, JavaScript, or unsafe patterns",
        "tip": "If code is shown, check: table layout? inline styles? no JS? Valid syntax?",
    },
    "source_relevance": {
        "agent": "knowledge",
        "title": "Source Relevance",
        "what": "Are retrieved sources relevant to the question?",
        "pass": "Sources match the topic domain (CSS support docs for CSS questions, etc.)",
        "fail": "Irrelevant sources or no sources for well-covered topics",
        "tip": "Do the cited sources actually relate to the question being asked?",
    },
    "completeness": {
        "agent": "knowledge",
        "title": "Completeness",
        "what": "Does the answer address all aspects of the question?",
        "pass": "Addresses all expected aspects; mentions client-specific considerations",
        "fail": "Missing major aspects or incomplete coverage",
        "tip": "Check expected_challenges — does the answer cover each aspect?",
    },
    # Innovation
    "technique_correctness": {
        "agent": "innovation",
        "title": "Technique Correctness",
        "what": "Is prototype code technically correct for the requested technique?",
        "pass": "Correct patterns (checkbox hacks, AMP boilerplate, @keyframes); HTML/CSS only; no JS",
        "fail": "Syntax errors, wrong patterns, or incorrect technique implementation",
        "tip": "Does the code use the right approach for this technique? Check for syntax errors.",
    },
    "fallback_quality": {
        "agent": "innovation",
        "title": "Fallback Quality",
        "what": "Does the response include a production-quality fallback for unsupported clients?",
        "pass": "Fallback is static HTML with meaningful content; AMP mentions MIME fallback",
        "fail": "Missing fallback or fallback would show blank/broken content",
        "tip": "What happens when the technique isn't supported? Is the fallback usable?",
    },
    "client_coverage_accuracy": {
        "agent": "innovation",
        "title": "Client Coverage Accuracy",
        "what": "Is the stated client coverage percentage realistic?",
        "pass": "Coverage claims are realistic (e.g., checkbox hacks ~30%, not 80%)",
        "fail": "Unrealistic coverage claims (overstating by >20%)",
        "tip": "Does the claimed support % match reality? Apple Mail supports most CSS; Outlook barely any.",
    },
    "feasibility_assessment": {
        "agent": "innovation",
        "title": "Feasibility Assessment",
        "what": "Does assessment include risk level, file size impact, and clear recommendation?",
        "pass": "Includes risk (high/medium/low), file size impact, and appropriate recommendation",
        "fail": "Missing risk/size/recommendation, or inappropriate recommendation",
        "tip": "Is the recommendation (ship/test/avoid) appropriate for the technique's maturity?",
    },
    "innovation_value": {
        "agent": "innovation",
        "title": "Innovation Value",
        "what": "Does response demonstrate genuine knowledge of technique trade-offs?",
        "pass": "Shows client-specific quirks, limitations, workarounds; actionable guidance",
        "fail": "Only generic code without email-specific context or trade-off analysis",
        "tip": "Does it go beyond 'here's the code' to explain when/why/why-not to use it?",
    },
}

QA_CHECK_INFO: dict[str, str] = {
    "html_validation": "HTML syntax validation (unclosed tags, missing doctype)",
    "css_support": "CSS property compatibility across email clients",
    "file_size": "Email file size within acceptable limits",
    "link_validation": "All links are valid and properly formatted",
    "spam_score": "Content doesn't trigger spam filters",
    "dark_mode": "Dark mode CSS and meta tags present",
    "accessibility": "Basic accessibility attributes present",
    "fallback": "MSO/Outlook fallback patterns present",
    "image_optimization": "Images have dimensions and optimization",
    "brand_compliance": "Brand colors and fonts used correctly",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().strip().splitlines() if line.strip()]


def build_review_data(traces_dir: Path) -> dict[str, Any]:
    """Build the review data focused on LLM-judged verdicts only."""
    data: dict[str, Any] = {
        "agents": {},
        "criterion_info": CRITERION_INFO,
        "qa_check_info": QA_CHECK_INFO,
        "stats": {},
    }

    total_human = 0
    total_auto = 0

    for agent in AGENTS:
        traces = load_jsonl(traces_dir / f"{agent}_traces.jsonl")
        verdicts = load_jsonl(traces_dir / f"{agent}_verdicts.jsonl")
        labels = load_jsonl(traces_dir / f"{agent}_human_labels.jsonl")

        trace_map = {t.get("trace_id", t.get("id", "")): t for t in traces}
        verdict_map: dict[str, dict[str, Any]] = {}
        for v in verdicts:
            verdict_map[v["trace_id"]] = v

        agent_data: dict[str, Any] = {"traces": [], "human_review_count": 0, "auto_count": 0}

        # Group labels by trace
        trace_labels: dict[str, list[dict[str, Any]]] = {}
        for label in labels:
            trace_labels.setdefault(label["trace_id"], []).append(label)

        for tid, tlabels in trace_labels.items():
            trace = trace_map.get(tid, {})
            verdict = verdict_map.get(tid, {})

            # Separate into categories
            human_needed = []
            auto_done = []

            for label in tlabels:
                criterion = label["criterion"]
                is_qa = label["judge_pass"] is None

                # Find reasoning from verdict
                reasoning = ""
                for cr in verdict.get("criteria_results", []):
                    if cr["criterion"] == criterion:
                        reasoning = cr.get("reasoning", "")
                        break

                is_deterministic = reasoning.startswith("[DETERMINISTIC]")
                is_llm = not is_qa and not is_deterministic

                entry = {
                    "criterion": criterion,
                    "judge_pass": label["judge_pass"],
                    "human_pass": label["human_pass"],
                    "reasoning": reasoning,
                    "notes": label.get("notes", ""),
                    "type": "qa" if is_qa else ("deterministic" if is_deterministic else "llm"),
                }

                if is_llm:
                    human_needed.append(entry)
                else:
                    auto_done.append(entry)

            # Build trace brief from input
            trace_input = trace.get("input", {})
            brief = trace_input.get(
                "brief", trace_input.get("question", trace_input.get("html", ""))
            )
            if isinstance(brief, dict):
                brief = json.dumps(brief, indent=2)

            html_output = ""
            output = trace.get("output", {})
            if isinstance(output, dict):
                html_output = output.get("html", output.get("answer", json.dumps(output, indent=2)))
            elif isinstance(output, str):
                html_output = output

            expected = trace.get("expected_challenges", [])
            dims = trace.get("dimensions", {})

            trace_entry = {
                "id": tid,
                "brief": brief[:2000] if isinstance(brief, str) else str(brief)[:2000],
                "html": html_output,
                "expected_challenges": expected,
                "dimensions": dims,
                "human_needed": human_needed,
                "auto_done": auto_done,
                "overall_pass": verdict.get("overall_pass"),
            }

            agent_data["traces"].append(trace_entry)
            agent_data["human_review_count"] += len(human_needed)
            agent_data["auto_count"] += len(auto_done)

        data["agents"][agent] = agent_data
        total_human += agent_data["human_review_count"]
        total_auto += agent_data["auto_count"]

    data["stats"] = {
        "total_rows": total_human + total_auto,
        "human_review": total_human,
        "auto_labeled": total_auto,
        "agents": len(AGENTS),
    }

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate eval review data")
    parser.add_argument("--traces-dir", type=Path, default=Path("traces"))
    parser.add_argument("--output", type=Path, default=Path("docs/eval-review-data.json"))
    args = parser.parse_args()

    data = build_review_data(args.traces_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2))

    print(f"Generated {args.output}")
    print(f"  Human review: {data['stats']['human_review']} rows")
    print(f"  Auto-labeled: {data['stats']['auto_labeled']} rows")
    print(f"  Total: {data['stats']['total_rows']} rows")


if __name__ == "__main__":
    main()
