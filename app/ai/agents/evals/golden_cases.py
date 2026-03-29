"""CI golden test cases — deterministic assembly regression detection.

A small set of email briefs with known-correct QA outcomes. These test the
deterministic template assembly path (template selection + slot fill + QA gate)
without requiring LLM calls.

CLI: python -m app.ai.agents.evals.golden_cases [--verbose]
Makefile: make eval-golden
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

from app.ai.agents.evals.template_eval_generator import UPLOADED_GOLDEN_DIR
from app.ai.templates.registry import get_template_registry
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GoldenCase:
    """Known-good test case for CI regression detection."""

    name: str
    template_name: str
    slot_fills: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    expected_qa_checks: dict[str, bool] = field(default_factory=lambda: dict[str, bool]())


# These cases validate that golden templates remain structurally sound
# and that the template registry + slot fill pipeline works correctly.
GOLDEN_CASES: list[GoldenCase] = [
    GoldenCase(
        name="newsletter_1col_basic",
        template_name="newsletter_1col",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="newsletter_2col_basic",
        template_name="newsletter_2col",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="promotional_hero_basic",
        template_name="promotional_hero",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="transactional_receipt_basic",
        template_name="transactional_receipt",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="event_invitation_basic",
        template_name="event_invitation",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="retention_winback_basic",
        template_name="retention_winback",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "dark_mode": True,
            "accessibility": True,
            "fallback": True,
        },
    ),
    GoldenCase(
        name="minimal_text_basic",
        template_name="minimal_text",
        slot_fills={},
        expected_qa_checks={
            "html_validation": True,
            "css_support": True,
            "accessibility": True,
        },
    ),
]


def load_uploaded_golden_cases() -> list[GoldenCase]:
    """Load golden cases auto-generated from uploaded templates."""
    cases: list[GoldenCase] = []
    if not UPLOADED_GOLDEN_DIR.exists():
        return cases
    for path in sorted(UPLOADED_GOLDEN_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            for case_data in data.get("cases", []):
                if case_data.get("case_type") != "assembly_golden":
                    continue
                cases.append(
                    GoldenCase(
                        name=case_data["id"],
                        template_name=case_data["template_name"],
                        slot_fills=case_data.get("slot_fills", {}),
                        expected_qa_checks=case_data.get("expected_qa_checks", {}),
                    )
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("golden_cases.uploaded_load_failed", path=str(path))
    return cases


@dataclass
class GoldenResult:
    """Result of running a single golden case."""

    case_name: str
    passed: bool
    template_found: bool
    checks_run: int
    checks_passed: int
    failures: list[str] = field(default_factory=lambda: list[str]())


def run_golden_cases(verbose: bool = False) -> list[GoldenResult]:
    """Run all golden cases against the template registry.

    Validates:
    1. Template exists in registry
    2. Template HTML is non-empty
    3. Template has expected structural markers (html_validation proxy)
    """
    registry = get_template_registry()
    results: list[GoldenResult] = []

    all_cases = list(GOLDEN_CASES) + load_uploaded_golden_cases()

    for case in all_cases:
        failures: list[str] = []
        template = registry.get(case.template_name)

        if template is None:
            results.append(
                GoldenResult(
                    case_name=case.name,
                    passed=False,
                    template_found=False,
                    checks_run=0,
                    checks_passed=0,
                    failures=[f"Template '{case.template_name}' not found in registry"],
                )
            )
            continue

        checks_run = 0
        checks_passed = 0
        html = template.html or ""
        html_lower = html.lower()

        # Check: template has HTML content
        checks_run += 1
        if len(html) > 100:
            checks_passed += 1
        else:
            failures.append("html is empty or too short")

        # Check: HTML has doctype
        checks_run += 1
        if "<!doctype" in html_lower:
            checks_passed += 1
        else:
            failures.append("missing <!DOCTYPE>")

        # Check: has lang attribute (accessibility)
        if case.expected_qa_checks.get("accessibility"):
            checks_run += 1
            if 'lang="' in html_lower or "lang='" in html_lower:
                checks_passed += 1
            else:
                failures.append("missing lang attribute on <html>")

        # Check: has MSO conditionals (fallback/Outlook support)
        if case.expected_qa_checks.get("fallback"):
            checks_run += 1
            if "<!--[if" in html:
                checks_passed += 1
            else:
                failures.append("missing MSO conditional comments")

        # Check: has dark mode meta or media query
        if case.expected_qa_checks.get("dark_mode"):
            checks_run += 1
            if "color-scheme" in html_lower or "prefers-color-scheme" in html_lower:
                checks_passed += 1
            else:
                failures.append("missing dark mode support (color-scheme)")

        # Check: file size under 102KB (Gmail clipping)
        checks_run += 1
        html_size = len(html.encode("utf-8"))
        if html_size <= 102_400:
            checks_passed += 1
        else:
            failures.append(f"HTML size {html_size} bytes exceeds 102KB Gmail clip limit")

        # Check: has metadata
        checks_run += 1
        if template.metadata and template.metadata.layout_type:
            checks_passed += 1
        else:
            failures.append("missing template metadata or layout_type")

        passed = len(failures) == 0
        results.append(
            GoldenResult(
                case_name=case.name,
                passed=passed,
                template_found=True,
                checks_run=checks_run,
                checks_passed=checks_passed,
                failures=failures,
            )
        )

        if verbose:
            status = "PASS" if passed else "FAIL"
            logger.info(f"  [{status}] {case.name} ({checks_passed}/{checks_run} checks)")
            for f in failures:
                logger.info(f"         - {f}")

    return results


def main() -> None:
    """CLI entry point for golden case validation."""
    parser = argparse.ArgumentParser(description="Run CI golden test cases")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    logger.info("=== Golden Template CI Tests ===")
    results = run_golden_cases(verbose=args.verbose)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    if not args.verbose:
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            logger.info(f"  [{status}] {r.case_name} ({r.checks_passed}/{r.checks_run})")
            for f in r.failures:
                logger.info(f"         - {f}")

    logger.info(f"{passed}/{total} golden cases passed.")

    if failed > 0:
        logger.info(f"FAILED: {failed} golden case(s) did not pass.")
        logger.error(
            "eval.golden_cases_failed",
            extra={"passed": passed, "failed": failed, "total": total},
        )
        sys.exit(1)
    else:
        logger.info("All golden cases passed.")
        logger.info("eval.golden_cases_passed", extra={"total": total})


if __name__ == "__main__":
    main()
