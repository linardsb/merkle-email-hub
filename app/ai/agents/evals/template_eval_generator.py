"""Generate comprehensive eval cases from uploaded templates.

Each uploaded template produces 5 eval cases:
1. Selection positive - brief that SHOULD select this template
2. Selection negative - brief that should NOT select this template
3. Slot fill - verify all required slots are filled with type-correct content
4. Assembly golden - deterministic assembly check (extends golden_cases.py)
5. QA pass-through - assembled HTML passes core QA checks

All generation is deterministic (no LLM calls).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.templates.models import GoldenTemplate, LayoutType
from app.core.logging import get_logger
from app.templates.upload.analyzer import AnalysisResult

logger = get_logger(__name__)

UPLOADED_GOLDEN_DIR = Path(__file__).parent / "data" / "uploaded_golden"

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _validate_template_name(name: str) -> None:
    """Validate template name to prevent path traversal."""
    if not _SAFE_NAME_RE.fullmatch(name):
        msg = f"Invalid template name: {name!r}"
        raise ValueError(msg)


# Layout-specific brief templates for positive selection
_POSITIVE_BRIEFS: dict[str, list[str]] = {
    "newsletter": [
        "Create a weekly newsletter with {section_count} content sections, article previews, and a footer with social links.",
        "Design a monthly digest email featuring curated articles and upcoming events for our subscribers.",
    ],
    "promotional": [
        "Design a promotional email with a bold hero image and a prominent call-to-action button for our seasonal sale.",
        "Build a product launch announcement email showcasing key features with a strong conversion CTA.",
    ],
    "transactional": [
        "Create an order confirmation email with order details, item summary, and shipping information.",
        "Design a receipt email with an itemized breakdown, payment confirmation, and support contact.",
    ],
    "event": [
        "Build an event invitation email with event details, speaker bios, and a registration CTA button.",
        "Create a webinar invitation with date/time, agenda highlights, and a 'Reserve Your Spot' button.",
    ],
    "retention": [
        "Design a re-engagement email for inactive subscribers with a personalized offer and clear value proposition.",
        "Create a win-back email with a 'We miss you' message, exclusive discount, and one-click reactivation.",
    ],
    "announcement": [
        "Build a company announcement email with a headline, supporting details, and a learn-more CTA.",
        "Create a product update notification with changelog highlights and a link to release notes.",
    ],
    "minimal": [
        "Create a simple text-focused email with a short message and a single call-to-action link.",
        "Build a minimal notification email with just a heading, one paragraph, and an action button.",
    ],
}

# Negative briefs - layout types that are DIFFERENT from each layout
_NEGATIVE_LAYOUT_MAP: dict[str, str] = {
    "newsletter": "transactional",
    "promotional": "transactional",
    "transactional": "promotional",
    "event": "transactional",
    "retention": "newsletter",
    "announcement": "transactional",
    "minimal": "promotional",
}


class TemplateEvalGenerator:
    """Generates 5 deterministic eval cases per uploaded template."""

    def generate(
        self,
        template: GoldenTemplate,
        analysis: AnalysisResult,
    ) -> list[dict[str, object]]:
        """Generate all eval cases for an uploaded template.

        Returns list of case dicts ready for JSON serialization.
        """
        name = template.metadata.name
        layout = template.metadata.layout_type
        now = datetime.now(UTC).isoformat()

        cases: list[dict[str, object]] = []

        # 1. Selection positive (1 case)
        cases.append(self._selection_positive(name, layout, analysis, now))

        # 2. Selection negative (1 case)
        cases.append(self._selection_negative(name, layout, now))

        # 3. Slot fill (1 case)
        cases.append(self._slot_fill(template, analysis, now))

        # 4. Assembly golden (1 case)
        cases.append(self._assembly_golden(template, now))

        # 5. QA pass-through (1 case)
        cases.append(self._qa_passthrough(template, now))

        logger.info(
            "template_eval.cases_generated",
            template=name,
            count=len(cases),
        )
        return cases

    def save(self, template_name: str, cases: list[dict[str, object]]) -> Path:
        """Save cases to per-template JSON file."""
        _validate_template_name(template_name)
        UPLOADED_GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        path = UPLOADED_GOLDEN_DIR / f"{template_name}.json"
        payload = {
            "template_name": template_name,
            "cases": cases,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        path.write_text(json.dumps(payload, indent=2, default=str))
        logger.info("template_eval.saved", path=str(path), count=len(cases))
        return path

    def delete(self, template_name: str) -> bool:
        """Delete eval cases for a template. Returns True if file existed."""
        _validate_template_name(template_name)
        path = UPLOADED_GOLDEN_DIR / f"{template_name}.json"
        if path.exists():
            path.unlink()
            logger.info("template_eval.deleted", template=template_name)
            return True
        return False

    def load_all(self) -> dict[str, list[dict[str, object]]]:
        """Load all uploaded template eval cases. Returns {template_name: cases}."""
        result: dict[str, list[dict[str, object]]] = {}
        if not UPLOADED_GOLDEN_DIR.exists():
            return result
        for path in sorted(UPLOADED_GOLDEN_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                result[data["template_name"]] = data["cases"]
            except (json.JSONDecodeError, KeyError):
                logger.warning("template_eval.load_failed", path=str(path))
        return result

    def load_for_template(self, template_name: str) -> list[dict[str, object]]:
        """Load eval cases for a specific template."""
        data = self.load_case_set(template_name)
        if data is None:
            return []
        cases: list[dict[str, object]] = data.get("cases", [])
        return cases

    def load_case_set(self, template_name: str) -> dict[str, Any] | None:
        """Load full case set (cases + metadata) for a template. Returns None if not found."""
        _validate_template_name(template_name)
        path = UPLOADED_GOLDEN_DIR / f"{template_name}.json"
        if not path.exists():
            return None
        try:
            result: dict[str, Any] = json.loads(path.read_text())
            return result
        except (json.JSONDecodeError, KeyError):
            return None

    # -- Case generators --

    def _selection_positive(
        self,
        name: str,
        layout: LayoutType,
        analysis: AnalysisResult,
        timestamp: str,
    ) -> dict[str, object]:
        """Brief that SHOULD select this template."""
        briefs = _POSITIVE_BRIEFS.get(layout, _POSITIVE_BRIEFS["newsletter"])
        section_count = len(analysis.sections)
        brief = briefs[0].format(section_count=section_count)

        if analysis.esp_platform:
            brief += f" Use {analysis.esp_platform.title()} personalisation syntax."

        complexity = (
            "complex"
            if len(analysis.slots) > 10
            else "moderate"
            if len(analysis.slots) > 5
            else "simple"
        )

        return {
            "id": f"uploaded-sel-pos-{name}",
            "case_type": "selection_positive",
            "template_name": name,
            "source": f"uploaded:{name}",
            "dimensions": {
                "layout_complexity": complexity,
                "content_type": layout,
                "client_quirk": "none",
                "brief_quality": "detailed_with_sections",
            },
            "brief": brief,
            "expected_template": name,
            "created_at": timestamp,
        }

    def _selection_negative(
        self,
        name: str,
        layout: LayoutType,
        timestamp: str,
    ) -> dict[str, object]:
        """Brief that should NOT select this template."""
        opposite_layout = _NEGATIVE_LAYOUT_MAP.get(layout, "transactional")
        neg_briefs = _POSITIVE_BRIEFS.get(opposite_layout, _POSITIVE_BRIEFS["transactional"])
        brief = neg_briefs[0].format(section_count=1)

        return {
            "id": f"uploaded-sel-neg-{name}",
            "case_type": "selection_negative",
            "template_name": name,
            "source": f"uploaded:{name}",
            "dimensions": {
                "layout_complexity": "simple",
                "content_type": opposite_layout,
                "client_quirk": "none",
                "brief_quality": "detailed_with_sections",
            },
            "brief": brief,
            "expected_template": name,  # should NOT match this
            "created_at": timestamp,
        }

    def _slot_fill(
        self,
        template: GoldenTemplate,
        analysis: AnalysisResult,
        timestamp: str,
    ) -> dict[str, object]:
        """Verify required slots are filled with type-correct content."""
        name = template.metadata.name
        required_slots = [s for s in template.slots if s.required]
        all_slots = list(template.slots)

        # Build expected fills from slot types
        slot_expectations: dict[str, dict[str, object]] = {}
        for slot in all_slots:
            slot_expectations[slot.slot_id] = {
                "slot_type": slot.slot_type,
                "required": slot.required,
                "max_chars": slot.max_chars,
            }

        return {
            "id": f"uploaded-slot-{name}",
            "case_type": "slot_fill",
            "template_name": name,
            "source": f"uploaded:{name}",
            "required_slot_count": len(required_slots),
            "total_slot_count": len(all_slots),
            "slot_expectations": slot_expectations,
            "layout_type": template.metadata.layout_type,
            "section_count": len(analysis.sections),
            "created_at": timestamp,
        }

    def _assembly_golden(
        self,
        template: GoldenTemplate,
        timestamp: str,
    ) -> dict[str, object]:
        """Deterministic assembly case - extends golden_cases.py."""
        name = template.metadata.name
        html = template.html or ""
        html_lower = html.lower()

        # Determine which QA checks this template should pass
        expected_checks: dict[str, bool] = {
            "html_validation": True,  # must have doctype + structure
            "css_support": True,
        }

        # Check for accessibility markers
        if 'lang="' in html_lower or "lang='" in html_lower:
            expected_checks["accessibility"] = True

        # Check for MSO conditionals
        if "<!--[if" in html:
            expected_checks["fallback"] = True

        # Check for dark mode
        if "color-scheme" in html_lower or "prefers-color-scheme" in html_lower:
            expected_checks["dark_mode"] = True

        return {
            "id": f"uploaded-golden-{name}",
            "case_type": "assembly_golden",
            "template_name": name,
            "source": f"uploaded:{name}",
            "expected_qa_checks": expected_checks,
            "slot_fills": {},  # empty fills = test raw template structure
            "created_at": timestamp,
        }

    def _qa_passthrough(
        self,
        template: GoldenTemplate,
        timestamp: str,
    ) -> dict[str, object]:
        """Assembled HTML should pass core QA checks without unexpected failures."""
        name = template.metadata.name
        html = template.html or ""

        return {
            "id": f"uploaded-qa-{name}",
            "case_type": "qa_passthrough",
            "template_name": name,
            "source": f"uploaded:{name}",
            "html_length": len(html),
            "has_esp_syntax": template.metadata.ideal_for == ("uploaded",),
            "created_at": timestamp,
        }
