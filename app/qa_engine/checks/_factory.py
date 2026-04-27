"""Parameterized factory for the 10 RuleEngine boilerplate QA checks.

Replaces 10 near-identical `*Check` classes (`html_validation`, `accessibility`,
`dark_mode`, `fallback`, `link_validation`, `file_size`, `spam_score`,
`image_optimization`, `brand_compliance`, `personalisation_syntax`) with
declarative entries in `ALL_CHECKS`. Each variant is encoded as a constructor
field; the `run()` orchestration is shared.

Bespoke checks (`css_audit`, `css_support`, `deliverability`, `liquid_syntax`)
remain as classes with their own `run()` implementations.
`rendering_resilience` is loaded directly by `qa_engine.service` and is not
registered in `ALL_CHECKS` to avoid chaos-engine recursion.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from lxml import html as lxml_html

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import RuleEngine, load_rules
from app.qa_engine.schemas import QACheckResult

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.qa_engine.checks import QACheckProtocol
    from app.qa_engine.rule_engine import Rule


EmptyStrategy = Literal["fail_error", "pass_info", "skip"]
SeverityMode = Literal["passed", "deduction"]
FailedSeverity = Literal["error", "warning"]


class RuleEngineCheck:
    """Factory for the standard RuleEngine + parse + score + filter pattern."""

    def __init__(
        self,
        *,
        name: str,
        rules_path: Path,
        cache_clear: Callable[[], None] | None = None,
        empty_strategy: EmptyStrategy = "fail_error",
        empty_message: str = "Empty HTML document",
        parse_error_message: str = "HTML could not be parsed",
        failed_severity: FailedSeverity = "warning",
        error_threshold: float | None = None,
        severity_mode: SeverityMode = "passed",
        summary_filter_prefix: str | None = None,
        no_issues_details: str | None = None,
        threshold_pass: bool = False,
        respects_disabled_config: bool = False,
        disabled_message: str = "",
        config_enricher: Callable[[QACheckConfig | None], QACheckConfig | None] | None = None,
        skip_predicate: Callable[[QACheckConfig | None], bool] | None = None,
        skip_message: str = "",
    ) -> None:
        self.name = name
        self._rules_path = rules_path
        self._cache_clear = cache_clear
        self._empty_strategy = empty_strategy
        self._empty_message = empty_message
        self._parse_error_message = parse_error_message
        self._failed_severity = failed_severity
        self._error_threshold = error_threshold
        self._severity_mode = severity_mode
        self._summary_filter_prefix = summary_filter_prefix
        self._no_issues_details = no_issues_details
        self._threshold_pass = threshold_pass
        self._respects_disabled_config = respects_disabled_config
        self._disabled_message = disabled_message
        self._config_enricher = config_enricher
        self._skip_predicate = skip_predicate
        self._skip_message = skip_message

        # Lazy: load rules + engine on first run() call.
        self._rules: list[Rule] | None = None
        self._engine: RuleEngine | None = None

    def _get_engine(self) -> RuleEngine:
        if self._engine is None:
            self._rules = load_rules(self._rules_path)
            self._engine = RuleEngine(self._rules)
        return self._engine

    def _empty_result(self) -> QACheckResult:
        if self._empty_strategy == "pass_info":
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details=self._empty_message,
                severity="info",
            )
        # "fail_error" — "skip" never produces an empty-result early return.
        return QACheckResult(
            check_name=self.name,
            passed=False,
            score=0.0,
            details=self._empty_message,
            severity="error",
        )

    def _compute_severity(self, *, passed: bool, total_deduction: float) -> str:
        if self._error_threshold is not None and total_deduction >= self._error_threshold:
            return "error"
        if self._severity_mode == "deduction":
            return "warning" if total_deduction > 0 else "info"
        return self._failed_severity if not passed else "info"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        if self._config_enricher is not None:
            config = self._config_enricher(config)

        if self._respects_disabled_config and config is not None and not config.enabled:
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details=self._disabled_message,
                severity="info",
            )

        if self._skip_predicate is not None and self._skip_predicate(config):
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details=self._skip_message,
                severity="info",
            )

        if self._empty_strategy != "skip" and (not html or not html.strip()):
            return self._empty_result()

        if self._cache_clear is not None:
            self._cache_clear()

        try:
            doc = lxml_html.document_fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details=self._parse_error_message,
                severity="error",
            )

        engine = self._get_engine()
        issues, total_deduction = engine.evaluate(doc, html, config)

        score = max(0.0, round(1.0 - total_deduction, 2))

        if self._summary_filter_prefix is not None:
            failure_issues = [i for i in issues if not i.startswith(self._summary_filter_prefix)]
        else:
            failure_issues = issues

        if self._threshold_pass:
            threshold = config.threshold if config is not None else 0.5
            passed = score >= threshold
        else:
            passed = len(failure_issues) == 0

        severity = self._compute_severity(passed=passed, total_deduction=total_deduction)

        if issues:
            details: str | None = "; ".join(issues)
        elif self._no_issues_details:
            details = self._no_issues_details
        else:
            details = None

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details=details,
            severity=severity,
        )


def get_check(name: str) -> QACheckProtocol:
    """Look up a registered check from `ALL_CHECKS` by `name`.

    Replaces direct class imports for the 10 boilerplate check classes that
    `_factory.RuleEngineCheck` now absorbs. Bespoke check classes (e.g.
    `LiquidSyntaxCheck`, `CssSupportCheck`, `RenderingResilienceCheck`) can
    still be imported directly from their modules.
    """
    from app.qa_engine.checks import ALL_CHECKS

    for check in ALL_CHECKS:
        if getattr(check, "name", None) == name:
            return check
    raise KeyError(f"Unknown check: {name}")
