"""Liquid template syntax validation check (QA check #13).

Validates Liquid template tags for correct syntax, balanced blocks,
filter validity, variable safety, and Braze/ESP-specific extensions.

Three-pass check:
1. python-liquid parse — catch syntax errors with line numbers
2. Rule engine — tag balance, filter validation, variable safety, nesting depth
3. Braze/ESP passthrough — detect and skip non-standard Liquid extensions
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.liquid_analyzer import (
    _LIQUID_OUTPUT_RE,
    KNOWN_FILTERS,
    LiquidAnalysis,
    analyze_liquid,
    clear_liquid_cache,
)
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

_LIQUID_TAG_RE = re.compile(r"\{[%{]", re.DOTALL)

# Deduction weights
_ERROR_DEDUCTION = 0.15
_WARNING_DEDUCTION = 0.05


class LiquidSyntaxCheck:
    """Validates Liquid template syntax in email HTML.

    Three-pass check:
    1. Structural analysis — detect syntax errors, unclosed blocks
    2. Filter & variable validation — unknown filters, missing defaults
    3. Braze/ESP passthrough — skip non-standard extensions
    """

    name = "liquid_syntax"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        """Run the Liquid syntax validation check."""
        if config and not config.enabled:
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="Liquid syntax check disabled by configuration",
                severity="info",
            )

        if not html or not html.strip():
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="Empty HTML document — no Liquid to validate",
                severity="info",
            )

        # Quick check: does HTML contain any Liquid syntax?
        if not _LIQUID_TAG_RE.search(html):
            return QACheckResult(
                check_name=self.name,
                passed=True,
                score=1.0,
                details="No Liquid template syntax detected",
                severity="info",
            )

        clear_liquid_cache()
        analysis = analyze_liquid(html)

        issues: list[str] = []
        total_deduction = 0.0

        # ── Pass 1: Structural parse errors ──
        for error in analysis.parse_errors:
            issues.append(f"Syntax: {error}")
            total_deduction += _ERROR_DEDUCTION

        # ── Pass 2: python-liquid parse validation ──
        parse_issues, parse_deduction = self._validate_with_python_liquid(html, analysis)
        issues.extend(parse_issues)
        total_deduction += parse_deduction

        # ── Pass 3: Filter & variable validation ──
        filter_issues, filter_deduction = self._validate_filters(analysis)
        issues.extend(filter_issues)
        total_deduction += filter_deduction

        variable_issues, var_deduction = self._validate_variables(html, analysis)
        issues.extend(variable_issues)
        total_deduction += var_deduction

        # ── Pass 4: Nesting depth ──
        max_nesting = config.params.get("max_nesting_depth", 5) if config else 5
        if analysis.nesting_depth > max_nesting:
            issues.append(f"Nesting: depth {analysis.nesting_depth} exceeds max {max_nesting}")
            total_deduction += _WARNING_DEDUCTION

        # ── Summary ──
        score = max(0.0, round(1.0 - total_deduction, 2))
        non_info = [i for i in issues if not i.startswith("Info:")]
        passed = len(non_info) == 0

        severity: str
        if total_deduction >= 0.30:
            severity = "error"
        elif total_deduction > 0:
            severity = "warning"
        else:
            severity = "info"

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=score,
            details="; ".join(issues) if issues else "Liquid syntax valid",
            severity=severity,
        )

    def _validate_with_python_liquid(
        self, html: str, analysis: LiquidAnalysis
    ) -> tuple[list[str], float]:
        """Try parsing with python-liquid library for syntax validation."""
        issues: list[str] = []
        deduction = 0.0

        # Skip python-liquid parse for Braze templates (non-standard extensions)
        if analysis.is_braze:
            return issues, deduction

        try:
            from liquid import Environment
            from liquid.exceptions import LiquidSyntaxError

            env = Environment()
            # Parse the full HTML as a Liquid template
            try:
                env.from_string(html)
            except LiquidSyntaxError as e:
                issues.append(f"Parse: {e}")
                deduction += _ERROR_DEDUCTION
        except ImportError:
            # python-liquid not installed — skip this pass
            pass
        except Exception:
            logger.debug("liquid_syntax.parse_error", exc_info=True)

        return issues, deduction

    def _validate_filters(self, analysis: LiquidAnalysis) -> tuple[list[str], float]:
        """Validate that filters used are known."""
        issues: list[str] = []
        deduction = 0.0

        for filter_name in analysis.filters_used:
            if filter_name not in KNOWN_FILTERS and not analysis.is_braze:
                issues.append(f"Filter: unknown filter '{filter_name}'")
                deduction += _WARNING_DEDUCTION

        return issues, deduction

    def _validate_variables(self, html: str, analysis: LiquidAnalysis) -> tuple[list[str], float]:
        """Check for variables without default filters."""
        issues: list[str] = []
        deduction = 0.0

        # Check for variables used without default filter
        for match in _LIQUID_OUTPUT_RE.finditer(html):
            expression = match.group(1).strip()
            if not expression:
                continue
            # Skip if it has a default filter
            if "| default" in expression or "|default" in expression:
                continue
            # Skip Braze content blocks
            if analysis.is_braze and (
                "content_blocks" in expression or "connected_content" in expression
            ):
                continue
            # Check for bare variables (no filters at all) in personalization contexts
            if "|" not in expression and "." in expression:
                # Deep property access without a default — potential undefined
                issues.append(f"Variable: '{expression}' used without | default filter")
                deduction += _WARNING_DEDUCTION
                if len(issues) >= 5:
                    break

        return issues, deduction
