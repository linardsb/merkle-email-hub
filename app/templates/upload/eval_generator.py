"""Auto-generate scaffolder eval test cases from uploaded template."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.templates.upload.analyzer import SectionInfo

logger = get_logger(__name__)

_EVAL_DATA_FILE = (
    Path(__file__).parents[2] / "ai" / "agents" / "evals" / "synthetic_data_uploaded.py"
)

# Brief templates by layout type
_BRIEF_TEMPLATES: dict[str, list[str]] = {
    "newsletter": [
        "Create a weekly newsletter for our {industry} audience with {section_count} content sections. Include a hero banner and multiple article previews.",
        "Design a monthly digest email with featured articles, upcoming events, and quick tips for {industry} professionals.",
        "Build a curated content roundup email with editorial picks and reader highlights.",
    ],
    "promotional": [
        "Design a promotional email for our {industry} sale event. Feature a hero image with a bold CTA button and supporting product highlights.",
        "Create an announcement email showcasing our new {industry} offering with a strong call-to-action.",
        "Build a launch email with hero visual, key benefits, and clear conversion path.",
    ],
    "transactional": [
        "Create an order confirmation email with order details table, item summary, and shipping information.",
        "Design a receipt email for {industry} purchases with itemized breakdown and support links.",
        "Build a shipping notification email with tracking information and delivery timeline.",
    ],
    "retention": [
        "Design a re-engagement email for inactive {industry} subscribers with a personalized offer and clear value proposition.",
        "Create a win-back email encouraging lapsed users to return with exclusive benefits.",
        "Build a 'we miss you' email with personalized recommendations based on past activity.",
    ],
}

_INDUSTRIES = ["e-commerce", "SaaS", "fintech", "health & wellness", "media"]


class EvalGenerator:
    """Generates synthetic eval test cases for a newly registered template."""

    def generate(
        self,
        template_name: str,
        layout_type: str,
        slot_count: int,
        esp_platform: str | None,
        sections: list[SectionInfo],
    ) -> list[dict[str, Any]]:
        """Generate 3-5 synthetic briefs that would plausibly select this template."""
        cases: list[dict[str, Any]] = []
        templates = _BRIEF_TEMPLATES.get(layout_type, _BRIEF_TEMPLATES["newsletter"])
        section_count = len(sections)

        complexity = "complex" if slot_count > 10 else "moderate" if slot_count > 5 else "simple"

        for idx, brief_template in enumerate(templates[:4]):
            industry = _INDUSTRIES[idx % len(_INDUSTRIES)]
            brief = brief_template.format(industry=industry, section_count=section_count)

            if esp_platform:
                brief += f" Use {esp_platform.title()} personalisation syntax."

            case: dict[str, Any] = {
                "id": f"scaff-uploaded-{template_name}-{idx + 1}",
                "dimensions": {
                    "layout_complexity": complexity,
                    "content_type": layout_type,
                    "client_quirk": "none",
                    "brief_quality": "detailed_with_sections",
                },
                "brief": brief,
                "expected_challenges": [f"uploaded_template_{layout_type}"],
                "expected_template": template_name,
            }
            cases.append(case)

        logger.info(
            "template_upload.eval_cases_generated",
            template=template_name,
            count=len(cases),
        )
        return cases

    def save_to_file(self, cases: list[dict[str, Any]], output_path: str | None = None) -> None:
        """Append generated cases to the eval data file."""
        path = Path(output_path) if output_path else _EVAL_DATA_FILE

        # Load existing cases
        existing: list[dict[str, Any]] = []
        if path.exists():
            content = path.read_text()
            # Extract the list from the Python file
            start = content.find("UPLOADED_CASES = ")
            if start >= 0:
                json_str = content[start + len("UPLOADED_CASES = ") :]
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    existing = json.loads(json_str)

        # Deduplicate by ID
        existing_ids = {c["id"] for c in existing}
        new_cases = [c for c in cases if c["id"] not in existing_ids]
        all_cases = existing + new_cases

        # Write back as Python file
        cases_json = json.dumps(all_cases, indent=2)
        content = f'"""Auto-generated eval test cases for uploaded templates."""\n\n# ruff: noqa: E501\n\nUPLOADED_CASES = {cases_json}\n'
        path.write_text(content)

        logger.info(
            "template_upload.eval_file_updated",
            path=str(path),
            total=len(all_cases),
            new=len(new_cases),
        )
