"""Mock trace and verdict generators for dry-run eval pipeline.

Used by --dry-run mode to exercise the full eval pipeline without LLM calls.
Produces deterministic outputs suitable for testing downstream tools
(error_analysis, calibration, qa_calibration, regression).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# Minimal valid email HTML for QA checks to process
MOCK_HTML = """\
<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>Mock Email</title>
<style>
  @media (prefers-color-scheme: dark) {
    .dark-bg { background-color: #1a1a2e !important; }
    .dark-text { color: #ffffff !important; }
  }
  [data-ogsc] .dark-bg { background-color: #1a1a2e !important; }
</style>
</head>
<body style="margin:0; padding:0; background-color:#ffffff;">
<!--[if mso]>
<table role="presentation" width="600" align="center"><tr><td>
<![endif]-->
<table role="presentation" width="100%" style="max-width:600px; margin:0 auto;">
  <tr>
    <td style="padding:20px; font-family:Arial,sans-serif; color:#333333;">
      <img src="https://placehold.co/600x200" alt="Hero banner for spring sale" \
width="600" height="200" style="display:block; width:100%; height:auto;">
      <h1>Mock Email Content</h1>
      <p>This is a mock email generated for eval pipeline testing.</p>
      <a href="https://example.com/cta" style="display:inline-block; padding:12px \
24px; background-color:#007bff; color:#ffffff; text-decoration:none;">Shop Now</a>
    </td>
  </tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</body>
</html>"""


def generate_mock_trace(
    case: dict[str, Any],
    agent: str,
) -> dict[str, Any]:
    """Generate a mock trace for a test case without calling LLM."""
    return {
        "id": case["id"],
        "agent": agent,
        "dimensions": case.get("dimensions", []),
        "input": case.get("input", {"brief": case.get("brief", "")}),
        "output": {
            "html": MOCK_HTML,
            "qa_results": [],
            "qa_passed": True,
            "model": "dry-run-mock",
        },
        "expected_challenges": case.get("expected_challenges", []),
        "elapsed_seconds": 0.01,
        "error": None,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def generate_mock_verdict(
    trace: dict[str, Any],
    criteria: list[dict[str, str]],
) -> dict[str, Any]:
    """Generate a mock judge verdict for a trace.

    Uses deterministic pass/fail based on trace_id hash + criterion index
    to produce ~20% failure rate.
    """
    trace_id: str = trace["id"]
    agent: str = trace["agent"]
    hash_val = hash(trace_id)

    criteria_results: list[dict[str, Any]] = []
    for i, crit in enumerate(criteria):
        passed = ((hash_val + i) % 5) != 0
        criteria_results.append(
            {
                "criterion": crit["criterion"],
                "passed": passed,
                "reasoning": (
                    f"{'Pass' if passed else 'Fail'}: "
                    f"mock evaluation of {crit['criterion']} for {trace_id}"
                ),
            }
        )

    overall_pass = all(cr["passed"] for cr in criteria_results)

    return {
        "trace_id": trace_id,
        "agent": agent,
        "overall_pass": overall_pass,
        "criteria_results": criteria_results,
        "error": None,
    }


SCAFFOLDER_CRITERIA: list[dict[str, str]] = [
    {"criterion": "brief_fidelity", "description": "HTML faithfully implements the brief"},
    {"criterion": "email_layout", "description": "Layout uses email-safe patterns"},
    {"criterion": "mso_conditionals", "description": "MSO conditionals correctly structured"},
    {"criterion": "table_structure", "description": "Table-based layout is correct"},
    {"criterion": "code_quality", "description": "Clean, well-structured HTML"},
]

DARK_MODE_CRITERIA: list[dict[str, str]] = [
    {"criterion": "color_coherence", "description": "Dark mode colors visually coherent"},
    {"criterion": "html_preservation", "description": "Original HTML preserved"},
    {"criterion": "outlook_selectors", "description": "Outlook dark mode selectors complete"},
    {"criterion": "media_query", "description": "prefers-color-scheme query present"},
    {"criterion": "meta_tags", "description": "color-scheme meta tags present"},
]

CONTENT_CRITERIA: list[dict[str, str]] = [
    {"criterion": "copy_quality", "description": "Copy is compelling and on-brand"},
    {"criterion": "tone_match", "description": "Tone matches request"},
    {"criterion": "spam_avoidance", "description": "No spam triggers"},
    {"criterion": "length_appropriate", "description": "Content length is appropriate"},
    {"criterion": "grammar", "description": "No grammar or spelling errors"},
]

AGENT_CRITERIA: dict[str, list[dict[str, str]]] = {
    "scaffolder": SCAFFOLDER_CRITERIA,
    "dark_mode": DARK_MODE_CRITERIA,
    "content": CONTENT_CRITERIA,
}


def generate_mock_blueprint_trace(
    brief_def: dict[str, str],
) -> dict[str, Any]:
    """Generate a mock blueprint eval trace."""
    brief_id: str = brief_def["id"]
    hash_val = hash(brief_id)
    retries = hash_val % 3

    return {
        "run_id": brief_id,
        "blueprint_name": "campaign",
        "brief": brief_def["brief"],
        "total_steps": 3 + retries,
        "total_retries": retries,
        "qa_passed": retries < 2,
        "final_html_length": len(MOCK_HTML),
        "total_tokens": 1500 + (retries * 500),
        "elapsed_seconds": 0.05,
        "node_trace": [
            {
                "node_name": "scaffolder",
                "node_type": "agent",
                "status": "completed",
                "iteration": 0,
                "duration_ms": 20,
                "summary": "Mock scaffolder output",
            },
            {
                "node_name": "qa_gate",
                "node_type": "gate",
                "status": "passed" if retries == 0 else "failed",
                "iteration": 0,
                "duration_ms": 5,
                "summary": "Mock QA gate",
            },
        ],
        "error": None,
    }
