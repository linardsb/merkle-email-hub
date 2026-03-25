# ruff: noqa: ARG001
"""Shared rule engine — loads YAML rule definitions and evaluates against lxml DOM.

Used by html_validation (email structure rules), accessibility (WCAG AA rules),
and future checks (dark_mode, fallback, spam, etc.).
Rule YAML files also serve as RAG knowledge base entries for agent context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml
from lxml.html import HtmlElement

from app.core.logging import get_logger
from app.qa_engine.check_config import QACheckConfig

logger = get_logger(__name__)


@dataclass(frozen=True)
class Rule:
    """A single validation rule loaded from YAML."""

    id: str
    group: str
    name: str
    check_type: str
    message: str
    wcag: str = ""
    level: str = ""
    selector: str = ""
    attr: str = ""
    attrs: tuple[str, ...] = ()
    value: str = ""
    values: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    min_count: int = 0
    max_count: int = -1
    custom_fn: str = ""
    deduction_key: str = ""
    default_deduction: float = 0.10
    per_element: bool = False
    cap_key: str = ""
    default_cap: int = 10


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""

    rule_id: str
    passed: bool
    issues: list[str] = field(default_factory=lambda: list[str]())
    deduction: float = 0.0


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

_rules_cache: dict[str, list[Rule]] = {}


def load_rules(yaml_path: Path) -> list[Rule]:
    """Load rules from a YAML file. Cached after first successful load."""
    cache_key = str(yaml_path)
    if cache_key in _rules_cache:
        return _rules_cache[cache_key]

    if not yaml_path.exists():
        logger.warning("rule_engine.yaml_missing", path=cache_key)
        return []

    try:
        with yaml_path.open() as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        logger.error("rule_engine.yaml_invalid", path=cache_key)
        return []

    rules: list[Rule] = []
    for entry in data.get("rules", []):
        try:
            rules.append(
                Rule(
                    id=entry["id"],
                    group=entry["group"],
                    name=entry["name"],
                    check_type=entry["check"],
                    message=entry["message"],
                    wcag=entry.get("wcag", ""),
                    level=entry.get("level", ""),
                    selector=entry.get("selector", ""),
                    attr=entry.get("attr", ""),
                    attrs=tuple(entry.get("attrs", ())),
                    value=entry.get("value", ""),
                    values=tuple(entry.get("values", ())),
                    patterns=tuple(entry.get("patterns", ())),
                    min_count=entry.get("min_count", 0),
                    max_count=entry.get("max_count", -1),
                    custom_fn=entry.get("custom_fn", ""),
                    deduction_key=entry.get("deduction_key", ""),
                    default_deduction=entry.get("default_deduction", 0.10),
                    per_element=entry.get("per_element", False),
                    cap_key=entry.get("cap_key", ""),
                    default_cap=entry.get("default_cap", 10),
                )
            )
        except (KeyError, TypeError) as exc:
            logger.warning("rule_engine.rule_skipped", path=cache_key, error=str(exc))

    _rules_cache[cache_key] = rules
    logger.info("rule_engine.rules_loaded", path=cache_key, count=len(rules))
    return rules


def clear_rules_cache() -> None:
    """Clear the rules cache. Useful for testing."""
    _rules_cache.clear()


# ---------------------------------------------------------------------------
# Check type protocol and registries
# ---------------------------------------------------------------------------


class CheckFn(Protocol):
    """Signature for check type evaluator functions."""

    def __call__(
        self,
        doc: HtmlElement,
        raw_html: str,
        rule: Rule,
        config: QACheckConfig | None,
    ) -> RuleResult: ...


class CustomCheckFn(Protocol):
    """Signature for custom check functions (complex logic)."""

    def __call__(
        self,
        doc: HtmlElement,
        raw_html: str,
        config: QACheckConfig | None,
    ) -> tuple[list[str], float]: ...


_CHECK_TYPES: dict[str, CheckFn] = {}
_CUSTOM_CHECKS: dict[str, CustomCheckFn] = {}


def register_check_type(name: str, fn: CheckFn) -> None:
    """Register a check type evaluator."""
    _CHECK_TYPES[name] = fn


def register_custom_check(name: str, fn: CustomCheckFn) -> None:
    """Register a named custom check function."""
    _CUSTOM_CHECKS[name] = fn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_deduction(rule: Rule, config: QACheckConfig | None) -> float:
    """Resolve deduction value from config params or rule default."""
    if config and rule.deduction_key:
        return float(config.params.get(rule.deduction_key, rule.default_deduction))
    return rule.default_deduction


def _get_cap(rule: Rule, config: QACheckConfig | None) -> int:
    """Resolve reporting cap from config params or rule default."""
    if config and rule.cap_key:
        return int(config.params.get(rule.cap_key, rule.default_cap))
    return rule.default_cap


def _select(doc: HtmlElement, selector: str) -> list[HtmlElement]:
    """Convert simple CSS-like selectors to lxml element lists."""
    # Simple tag: "img", "table", "a"
    if re.match(r"^[a-z]+$", selector):
        return list(doc.iter(selector))
    # Tag with attribute: "meta[charset]", "link[rel='stylesheet']"
    m = re.match(r"^([a-z]+)\[([a-z-]+)(?:=['\"]?([^'\"]*)['\"]?)?\]$", selector)
    if m:
        tag, attr, val = m.group(1), m.group(2), m.group(3)
        elements = list(doc.iter(tag))
        if val is not None:
            return [e for e in elements if (e.get(attr) or "").lower() == val.lower()]
        return [e for e in elements if e.get(attr) is not None]
    # Scoped: "head meta[charset]" -> find meta[charset] under head
    parts = selector.split()
    if len(parts) == 2:
        parent_tag = parts[0]
        parents = list(doc.iter(parent_tag))
        child_selector = parts[1]
        results: list[HtmlElement] = []
        for p in parents:
            results.extend(_select(p, child_selector))
        return results
    # Fallback: try xpath
    try:
        result: list[HtmlElement] = doc.xpath(f".//{selector.replace(' ', '//')}")
        return result
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Check type evaluators
# ---------------------------------------------------------------------------


def _check_attr_present(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Element(s) matching selector must have the specified attr(s)."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    attrs_to_check = list(rule.attrs) if rule.attrs else ([rule.attr] if rule.attr else [])

    for el in elements:
        tag = el.tag if isinstance(el.tag, str) else "?"
        missing = [a for a in attrs_to_check if el.get(a) is None]
        if missing:
            if len(issues) < cap:
                issues.append(f"{rule.message}: <{tag}> missing {', '.join(missing)}")
            if rule.per_element:
                total += deduction
            elif total == 0.0:
                total = deduction

    if issues and not rule.per_element and total == 0.0:
        total = deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_attr_value(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Attribute must equal expected value."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        tag = el.tag if isinstance(el.tag, str) else "?"
        actual = el.get(rule.attr, "")
        if rule.values:
            if actual not in rule.values:
                if len(issues) < cap:
                    issues.append(f'{rule.message}: <{tag}> {rule.attr}="{actual}"')
                if rule.per_element:
                    total += deduction
                elif total == 0.0:
                    total = deduction
        elif actual != rule.value:
            if len(issues) < cap:
                issues.append(f'{rule.message}: <{tag}> {rule.attr}="{actual}"')
            if rule.per_element:
                total += deduction
            elif total == 0.0:
                total = deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_attr_empty(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Attribute must be present and be empty string."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        tag = el.tag if isinstance(el.tag, str) else "?"
        val = el.get(rule.attr)
        if val is None or val != "":
            if len(issues) < cap:
                issues.append(f"{rule.message}: <{tag}>")
            if rule.per_element:
                total += deduction
            elif total == 0.0:
                total = deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_attr_pattern(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Attribute value must match regex pattern(s). All patterns must match (AND)."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        tag = el.tag if isinstance(el.tag, str) else "?"
        val = el.get(rule.attr, "")
        for pattern in rule.patterns:
            if not re.search(pattern, val):
                if len(issues) < cap:
                    issues.append(f'{rule.message}: <{tag}> {rule.attr}="{val}"')
                if rule.per_element:
                    total += deduction
                elif total == 0.0:
                    total = deduction
                break

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_attr_absent(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Attribute must NOT be present on matching elements."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        tag = el.tag if isinstance(el.tag, str) else "?"
        if el.get(rule.attr) is not None:
            if len(issues) < cap:
                issues.append(f"{rule.message}: <{tag}> has {rule.attr}")
            if rule.per_element:
                total += deduction
            elif total == 0.0:
                total = deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_element_present(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """At least one element matching selector must exist."""
    elements = _select(doc, rule.selector) if rule.selector else []
    min_required = rule.min_count if rule.min_count > 0 else 1

    if len(elements) >= min_required:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    return RuleResult(
        rule_id=rule.id,
        passed=False,
        issues=[rule.message],
        deduction=deduction,
    )


def _check_element_absent(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """No elements matching selector should exist."""
    elements = _select(doc, rule.selector) if rule.selector else []

    if len(elements) == 0:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    return RuleResult(
        rule_id=rule.id,
        passed=False,
        issues=[rule.message],
        deduction=deduction,
    )


def _check_element_count(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Count of matching elements must be within min_count..max_count."""
    elements = _select(doc, rule.selector) if rule.selector else []
    count = len(elements)

    in_range = count >= rule.min_count
    if rule.max_count >= 0:
        in_range = in_range and count <= rule.max_count

    if in_range:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    return RuleResult(
        rule_id=rule.id,
        passed=False,
        issues=[f"{rule.message} (found {count})"],
        deduction=deduction,
    )


def _check_parent_has(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Each matching element's parent must have specified tag name from values."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        parent = el.getparent()
        if parent is None:
            continue
        if not isinstance(parent.tag, str):
            continue
        parent_tag = parent.tag.lower()
        if parent_tag not in rule.values:
            tag = el.tag if isinstance(el.tag, str) else "?"
            if len(issues) < cap:
                issues.append(f"{rule.message}: <{tag}> inside <{parent_tag}>")
            if rule.per_element:
                total += deduction
            elif total == 0.0:
                total = deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_children_match(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """First child of matching element must meet criteria."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        children = [c for c in el if isinstance(c.tag, str)]
        if not children or str(children[0].tag).lower() != rule.value:
            if len(issues) == 0:
                issues.append(rule.message)
                total += deduction

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_text_content(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Element text content must match (or not match) pattern."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if not elements:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    cap = _get_cap(rule, config)
    issues: list[str] = []
    total = 0.0

    for el in elements:
        text = (el.text_content() or "").strip()
        for pattern in rule.patterns:
            negate = pattern.startswith("!")
            p = pattern[1:] if negate else pattern
            match = bool(re.search(p, text))
            if (negate and match) or (not negate and not match):
                if len(issues) < cap:
                    issues.append(rule.message)
                total += deduction
                break

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_sibling_check(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Detect consecutive sibling elements sharing same attribute value."""
    elements = _select(doc, rule.selector) if rule.selector else []
    if len(elements) < 2:
        return RuleResult(rule_id=rule.id, passed=True)

    deduction = _get_deduction(rule, config)
    issues: list[str] = []
    total = 0.0

    prev_val: str | None = None
    for el in elements:
        val = el.get(rule.attr)
        if val and val == prev_val:
            issues.append(rule.message)
            total += deduction
            break
        prev_val = val

    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_style_contains(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """CSS in <style> blocks or inline style must match pattern."""
    deduction = _get_deduction(rule, config)
    issues: list[str] = []

    # Collect all CSS text
    css_texts: list[str] = []
    for style in doc.iter("style"):
        if style.text:
            css_texts.append(style.text)
    # Also check inline styles
    for el in doc.iter():
        if isinstance(el.tag, str):
            inline = el.get("style")
            if inline:
                css_texts.append(inline)

    combined = " ".join(css_texts)

    for pattern in rule.patterns:
        if not re.search(pattern, combined, re.IGNORECASE):
            issues.append(rule.message)
            break

    total = deduction if issues else 0.0
    return RuleResult(rule_id=rule.id, passed=len(issues) == 0, issues=issues, deduction=total)


def _check_raw_html_pattern(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Regex match against raw HTML string.

    Convention: fails when pattern NOT found (checks for required patterns).
    For "must not exist" checks, use element_absent or custom.
    """
    deduction = _get_deduction(rule, config)

    for pattern in rule.patterns:
        if not re.search(pattern, raw_html, re.IGNORECASE):
            return RuleResult(
                rule_id=rule.id,
                passed=False,
                issues=[rule.message],
                deduction=deduction,
            )

    return RuleResult(rule_id=rule.id, passed=True)


def _check_custom(
    doc: HtmlElement,
    raw_html: str,
    rule: Rule,
    config: QACheckConfig | None,
) -> RuleResult:
    """Delegates to a named Python function via _CUSTOM_CHECKS."""
    fn = _CUSTOM_CHECKS.get(rule.custom_fn)
    if fn is None:
        logger.warning(
            "rule_engine.custom_fn_missing",
            rule_id=rule.id,
            custom_fn=rule.custom_fn,
        )
        return RuleResult(rule_id=rule.id, passed=True)

    issues, total_deduction = fn(doc, raw_html, config)
    return RuleResult(
        rule_id=rule.id,
        passed=len(issues) == 0,
        issues=issues,
        deduction=total_deduction,
    )


# ---------------------------------------------------------------------------
# Register all check types
# ---------------------------------------------------------------------------

register_check_type("attr_present", _check_attr_present)
register_check_type("attr_value", _check_attr_value)
register_check_type("attr_empty", _check_attr_empty)
register_check_type("attr_pattern", _check_attr_pattern)
register_check_type("attr_absent", _check_attr_absent)
register_check_type("element_present", _check_element_present)
register_check_type("element_absent", _check_element_absent)
register_check_type("element_count", _check_element_count)
register_check_type("parent_has", _check_parent_has)
register_check_type("children_match", _check_children_match)
register_check_type("text_content", _check_text_content)
register_check_type("sibling_check", _check_sibling_check)
register_check_type("style_contains", _check_style_contains)
register_check_type("raw_html_pattern", _check_raw_html_pattern)
register_check_type("custom", _check_custom)


# ---------------------------------------------------------------------------
# RuleEngine orchestrator
# ---------------------------------------------------------------------------


class RuleEngine:
    """Evaluates a set of rules against an HTML document."""

    def __init__(self, rules: list[Rule]) -> None:
        self.rules = rules

    def evaluate(
        self,
        doc: HtmlElement,
        raw_html: str,
        config: QACheckConfig | None = None,
    ) -> tuple[list[str], float]:
        """Run all rules, return (all_issues, total_deduction)."""
        all_issues: list[str] = []
        total_deduction = 0.0

        for rule in self.rules:
            check_fn = _CHECK_TYPES.get(rule.check_type)
            if check_fn is None:
                logger.warning(
                    "rule_engine.unknown_check_type",
                    rule_id=rule.id,
                    check_type=rule.check_type,
                )
                continue

            result = check_fn(doc, raw_html, rule, config)
            if not result.passed:
                all_issues.extend(result.issues)
                total_deduction += result.deduction

        return all_issues, total_deduction
