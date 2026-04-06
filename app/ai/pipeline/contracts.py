"""Quality contracts for pipeline stage gates.

A contract is a set of assertions that an agent's output must pass before
artifacts propagate to the next DAG level. Each assertion maps to a built-in
check function registered in ``_CHECK_REGISTRY``.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from lxml import etree
from lxml.html import document_fromstring

from app.ai.shared import sanitize_html_xss
from app.core.logging import get_logger
from app.qa_engine.schemas import QACheckResult

logger = get_logger(__name__)

# ── Data structures ──────────────────────────────────────────────────────────

Operator = Literal[">=", "<=", "==", "contains", "not_contains"]


@dataclass(frozen=True, slots=True)
class Assertion:
    """Single check within a contract."""

    check: str
    operator: Operator = ">="
    threshold: Any = None


@dataclass(frozen=True, slots=True)
class Contract:
    """Named collection of assertions validated together."""

    name: str
    assertions: tuple[Assertion, ...]


@dataclass(frozen=True, slots=True)
class AssertionFailure:
    """Detail about a single failed assertion."""

    assertion: Assertion
    actual_value: Any
    message: str


@dataclass(frozen=True, slots=True)
class ContractResult:
    """Outcome of validating a contract against HTML + metadata."""

    passed: bool
    failures: tuple[AssertionFailure, ...]
    duration_ms: int


# ── Built-in check functions ─────────────────────────────────────────────────

_LAYOUT_CSS_RE = re.compile(
    r"(?:^|;)\s*(?:width|flex|float|columns)\s*:",
    re.IGNORECASE,
)


def _check_html_valid(html: str, _metadata: dict[str, Any]) -> bool:
    try:
        document_fromstring(html)
    except etree.ParserError:
        return False
    return True


def _check_min_size(html: str, _metadata: dict[str, Any]) -> int:
    return len(html.encode("utf-8"))


def _check_max_size(html: str, _metadata: dict[str, Any]) -> int:
    return len(html.encode("utf-8"))


def _check_has_table_layout(html: str, _metadata: dict[str, Any]) -> bool:
    try:
        doc = document_fromstring(html)
    except etree.ParserError:
        return False
    if not doc.cssselect("table"):
        return False
    for tag in ("div", "p"):
        for el in doc.cssselect(tag):
            style = el.get("style", "")
            if _LAYOUT_CSS_RE.search(style):
                return False
    return True


def _check_dark_mode_present(html: str, _metadata: dict[str, Any]) -> bool:
    return "prefers-color-scheme" in html or "color-scheme" in html


def _check_no_critical_qa(_html: str, metadata: dict[str, Any]) -> bool:
    results: list[QACheckResult] = metadata.get("qa_results", [])
    return all(r.severity != "error" or r.passed for r in results)


def _check_fidelity_above(_html: str, metadata: dict[str, Any]) -> float:
    return float(metadata.get("fidelity", 0.0))


def _check_no_xss(html: str, _metadata: dict[str, Any]) -> bool:
    return sanitize_html_xss(html) == html


_CHECK_REGISTRY: dict[str, Any] = {
    "html_valid": _check_html_valid,
    "min_size": _check_min_size,
    "max_size": _check_max_size,
    "has_table_layout": _check_has_table_layout,
    "dark_mode_present": _check_dark_mode_present,
    "no_critical_qa": _check_no_critical_qa,
    "fidelity_above": _check_fidelity_above,
    "no_xss": _check_no_xss,
}


# ── Evaluation helpers ───────────────────────────────────────────────────────


def _evaluate(operator: Operator, actual: Any, threshold: Any) -> bool:  # noqa: ANN401
    if operator == ">=":
        return actual >= threshold  # type: ignore[no-any-return]
    if operator == "<=":
        return actual <= threshold  # type: ignore[no-any-return]
    if operator == "==":
        return actual == threshold  # type: ignore[no-any-return]
    if operator == "contains":
        return threshold in actual
    if operator == "not_contains":
        return threshold not in actual
    return False  # pragma: no cover


def _describe_failure(assertion: Assertion, actual: Any) -> str:  # noqa: ANN401
    return (
        f"Check '{assertion.check}' failed: "
        f"actual={actual!r} {assertion.operator} threshold={assertion.threshold!r}"
    )


# ── Contract validator ───────────────────────────────────────────────────────


class ContractValidator:
    """Validates HTML + metadata against a contract's assertions."""

    async def validate(
        self,
        contract: Contract,
        html: str,
        metadata: dict[str, Any] | None = None,
    ) -> ContractResult:
        start = time.monotonic()
        failures: list[AssertionFailure] = []
        meta = metadata or {}

        for assertion in contract.assertions:
            check_fn = _CHECK_REGISTRY.get(assertion.check)
            if check_fn is None:
                failures.append(
                    AssertionFailure(assertion, None, f"Unknown check: {assertion.check}")
                )
                continue
            actual = check_fn(html, meta)
            if not _evaluate(assertion.operator, actual, assertion.threshold):
                failures.append(
                    AssertionFailure(assertion, actual, _describe_failure(assertion, actual))
                )

        elapsed = int((time.monotonic() - start) * 1000)
        return ContractResult(
            passed=len(failures) == 0,
            failures=tuple(failures),
            duration_ms=elapsed,
        )


# ── YAML contract loader ────────────────────────────────────────────────────


@lru_cache
def load_contract(path: Path) -> Contract:
    """Load a contract definition from a YAML file."""
    with path.open() as f:
        data = yaml.safe_load(f)

    assertions = tuple(
        Assertion(
            check=a["check"],
            operator=a.get("operator", ">="),
            threshold=a.get("threshold"),
        )
        for a in data["assertions"]
    )
    return Contract(name=data["name"], assertions=assertions)
