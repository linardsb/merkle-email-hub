"""CSS email client support check — ontology + syntax validation."""

from __future__ import annotations

import pathlib

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.knowledge.ontology.query import unsupported_css_in_html
from app.knowledge.ontology.registry import load_ontology
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

_DEFAULT_ERROR_DEDUCTION = 0.2
_DEFAULT_WARNING_DEDUCTION = 0.1
_DEFAULT_MAX_DETAILS = 10

_RULES_PATH = pathlib.Path(__file__).resolve().parent.parent / "rules" / "css_support.yaml"


class CssSupportCheck:
    """Checks for CSS properties with poor email client support + syntax validation.

    Two-pass check:
    1. Ontology scan — flags CSS properties unsupported by major email clients
    2. Syntax validation — cssutils parsing, vendor prefixes, external stylesheets
    """

    name = "css_support"

    def __init__(self) -> None:
        self._rules = load_rules(_RULES_PATH)
        self._engine = RuleEngine(self._rules)

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        error_deduction: float = (
            config.params.get("error_deduction", _DEFAULT_ERROR_DEDUCTION)
            if config
            else _DEFAULT_ERROR_DEDUCTION
        )
        warning_deduction: float = (
            config.params.get("warning_deduction", _DEFAULT_WARNING_DEDUCTION)
            if config
            else _DEFAULT_WARNING_DEDUCTION
        )
        max_details: int = (
            config.params.get("max_issues_in_details", _DEFAULT_MAX_DETAILS)
            if config
            else _DEFAULT_MAX_DETAILS
        )

        # ── Pass 1: Ontology-based client support scan (existing) ──
        ontology_issues = unsupported_css_in_html(html)

        for issue in ontology_issues:
            if issue["severity"] == "error" and issue["fallback_available"]:
                issue["severity"] = "warning"

        actionable = [i for i in ontology_issues if i["severity"] in ("error", "warning")]
        errors = [i for i in actionable if i["severity"] == "error"]
        warnings = [i for i in actionable if i["severity"] == "warning"]

        detail_parts: list[str] = []
        for issue in actionable[:max_details]:
            prop_str = f"{issue['property_name']}"
            if issue["value"]:
                prop_str += f": {issue['value']}"
            client_count = issue["unsupported_count"]
            fallback = " (fallback available)" if issue["fallback_available"] else ""
            detail_parts.append(f"Unsupported: {prop_str} ({client_count} clients){fallback}")

        if len(actionable) > max_details:
            detail_parts.append(f"... and {len(actionable) - max_details} more")

        # Engine-level summary
        registry = load_ontology()
        engine_warnings: set[str] = set()
        for issue in actionable:
            prop_id = str(issue["property_id"])
            unsupported_engines = registry.engines_not_supporting(prop_id)
            for engine in unsupported_engines:
                share = registry.engine_market_share(engine)
                engine_warnings.add(
                    f"Engine: {engine.value.title()} ({share:.1f}% share) — no support for {issue['property_name']}"
                )

        for warning in sorted(engine_warnings)[:5]:
            detail_parts.append(warning)

        ontology_score_loss = len(errors) * error_deduction + len(warnings) * warning_deduction

        # ── Pass 2: Syntax validation via rule engine (new) ──
        doc: HtmlElement = lxml_html.document_fromstring(html)
        syntax_issues, syntax_deduction = self._engine.evaluate(doc, html, config)

        # Merge results
        detail_parts.extend(syntax_issues[:max_details])

        total_deduction = ontology_score_loss + syntax_deduction
        score = max(0.0, round(1.0 - total_deduction, 2))
        has_errors = len(errors) > 0 or syntax_deduction >= 0.25
        severity = "error" if has_errors else ("warning" if detail_parts else "info")

        return QACheckResult(
            check_name=self.name,
            passed=not has_errors,
            score=score,
            details="; ".join(detail_parts) if detail_parts else None,
            severity=severity,
        )
