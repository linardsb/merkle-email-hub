"""Brand compliance check — per-project color, typography, element, and pattern validation.

Uses the shared rule engine with rules loaded from rules/brand_compliance.yaml.
Brand rules are configured per-project via qa_profile JSON column params:
  allowed_colors, required_fonts, required_elements, forbidden_patterns.
When no rules are configured, check passes with info message (backward-compatible).

Implements 7 rules across 5 groups:
A (1): Color Compliance — validate CSS colors against brand palette
B (2): Typography — validate font-family against approved fonts
C (3-5): Required Elements — footer, logo, unsubscribe link
D (6): Forbidden Patterns — regex text pattern matching
E (7): Summary — informational, no deduction
"""

from __future__ import annotations

from pathlib import Path

from lxml import html as lxml_html
from pydantic import ValidationError

# Import custom checks to ensure brand check functions are registered
import app.qa_engine.custom_checks  # noqa: F401  # pyright: ignore[reportUnusedImport]
from app.projects.design_system import design_system_to_brand_rules, load_design_system
from app.qa_engine.brand_analyzer import clear_brand_cache
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "brand_compliance.yaml"


def _has_brand_rules(config: QACheckConfig | None) -> bool:
    """Check if any brand rules are configured."""
    if not config:
        return False
    params = config.params
    return bool(
        params.get("allowed_colors")
        or params.get("required_fonts")
        or params.get("required_elements")
        or params.get("forbidden_patterns")
    )


def _enrich_config_from_design_system(config: QACheckConfig | None) -> QACheckConfig | None:
    """If no explicit brand rules but _design_system is in params, derive brand rules.

    The QA runner passes the project's design_system raw dict via params["_design_system"]
    when running checks for a project that has a design system configured.
    """
    if config is None:
        return None
    if _has_brand_rules(config):
        return config
    ds_raw = config.params.get("_design_system")
    if not ds_raw:
        return config
    try:
        ds = load_design_system(ds_raw)
    except ValidationError:
        return config
    if ds is None:
        return config
    derived = design_system_to_brand_rules(ds)
    # Merge derived rules into params (don't overwrite existing), strip internal key
    merged_params = {k: v for k, v in config.params.items() if k != "_design_system"}
    merged_params.update(derived)
    return QACheckConfig(
        enabled=config.enabled,
        severity=config.severity,
        threshold=config.threshold,
        params=merged_params,
    )


class BrandComplianceCheck:
    """Per-project brand compliance validation via YAML rule engine.

    When no brand rules are configured (default), returns passed=True with info message.
    When rules exist, validates HTML against project-specific brand guidelines.
    """

    name = "brand_compliance"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        config = _enrich_config_from_design_system(config)

        if config and not config.enabled:
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="Brand compliance check disabled by configuration",
                severity="info",
            )

        # No brand rules configured → backward-compatible pass
        if not _has_brand_rules(config):
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="No brand rules configured — set up brand profile for enforcement",
                severity="info",
            )

        clear_brand_cache()

        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Empty HTML document",
                severity="error",
            )

        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="HTML could not be parsed",
                severity="error",
            )

        issues, total_deduction = self._engine.evaluate(doc, html, config)

        score = max(0.0, round(1.0 - total_deduction, 2))
        # Filter summary from pass/fail
        failure_issues = [i for i in issues if not i.startswith("Brand compliance:")]
        passed = len(failure_issues) == 0

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else "All brand rules satisfied",
            severity="error" if total_deduction >= 0.50 else ("warning" if not passed else "info"),
        )
