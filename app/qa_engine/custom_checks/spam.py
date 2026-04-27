# ruff: noqa: ARG001
"""Spam score custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.rule_engine import register_custom_check

# ---------------------------------------------------------------------------
# Spam Score — trigger phrases, formatting heuristics, obfuscation detection
# ---------------------------------------------------------------------------

_SPAM_TRIGGERS_PATH = Path(__file__).resolve().parent.parent / "data" / "spam_triggers.yaml"

_spam_trigger_cache: list[dict[str, str | float]] | None = None


def _load_spam_triggers() -> list[dict[str, str | float]]:
    """Load and cache spam trigger phrases from YAML."""
    global _spam_trigger_cache
    if _spam_trigger_cache is not None:
        return _spam_trigger_cache

    import yaml

    if not _SPAM_TRIGGERS_PATH.exists():
        _spam_trigger_cache = []
        return _spam_trigger_cache

    with _SPAM_TRIGGERS_PATH.open() as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    triggers: list[dict[str, str | float]] = data.get("triggers", [])
    _spam_trigger_cache = triggers
    return _spam_trigger_cache


# Pre-compiled regex cache for trigger phrases
_trigger_patterns: dict[str, re.Pattern[str]] = {}


def _get_trigger_pattern(phrase: str) -> re.Pattern[str]:
    """Get pre-compiled word-boundary regex for a trigger phrase."""
    if phrase not in _trigger_patterns:
        _trigger_patterns[phrase] = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    return _trigger_patterns[phrase]


def _extract_text(raw_html: str) -> str:
    """Strip HTML tags to get plain text for trigger matching."""
    return re.sub(r"<[^>]+>", " ", raw_html)


def spam_trigger_scan(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Scan email body text for known spam trigger phrases with weighted scoring."""
    triggers = _load_spam_triggers()
    text = _extract_text(raw_html)

    issues: list[str] = []
    total_deduction = 0.0
    max_reported: int = int(config.params.get("max_triggers_reported", 10) if config else 10)

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        weight = float(trigger.get("weight", 0.10))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)

        matches = pattern.findall(text)
        if matches:
            total_deduction += weight
            if len(issues) < max_reported:
                issues.append(f"'{phrase}' ({category}, -{weight:.2f})")

    return issues, total_deduction


def spam_subject_triggers(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check subject line (title tag) for spam triggers — 3x weight multiplier."""
    triggers = _load_spam_triggers()
    subject_multiplier = float(
        config.params.get("subject_weight_multiplier", 3.0) if config else 3.0
    )

    # Extract subject from <title> tag
    titles = list(doc.iter("title"))
    if not titles:
        return [], 0.0

    subject_text = (titles[0].text_content() or "").strip()
    if not subject_text:
        return [], 0.0

    issues: list[str] = []
    total_deduction = 0.0

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        weight = float(trigger.get("weight", 0.10))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)

        if pattern.search(subject_text):
            adjusted_weight = weight * subject_multiplier
            total_deduction += adjusted_weight
            issues.append(f"Subject: '{phrase}' ({category}, -{adjusted_weight:.2f})")

    return issues, total_deduction


# Formatting heuristic patterns (pre-compiled at module load)
_EXCESSIVE_PUNCTUATION = re.compile(r"[!?]{3,}")
_ALL_CAPS_WORD = re.compile(r"\b[A-Z]{2,}\b")
_OBFUSCATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\w*\d+\w*\b"), "leet-speak"),  # words with digits mixed in
]
# Common leet-speak substitutions
_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "@": "a",
    "$": "s",
}
_LEET_DECODE = re.compile(r"[0134578@$]")
_KNOWN_LEET_WORDS = frozenset(
    {
        "free",
        "sale",
        "discount",
        "offer",
        "cash",
        "prize",
        "bonus",
        "credit",
        "viagra",
        "casino",
        "winner",
    }
)


def spam_excessive_punctuation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect excessive punctuation (3+ consecutive ! or ?)."""
    text = _extract_text(raw_html)
    matches = _EXCESSIVE_PUNCTUATION.findall(text)
    deduction = float(
        config.params.get("deduction_excessive_punctuation", 0.10) if config else 0.10
    )

    if not matches:
        return [], 0.0

    issues = [f"Excessive punctuation: {len(matches)} instance(s) of 3+ consecutive !/?"]
    return issues, deduction


def spam_all_caps_words(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect sequences of 3+ all-caps words."""
    text = _extract_text(raw_html)
    words = text.split()
    deduction = float(config.params.get("deduction_all_caps", 0.10) if config else 0.10)

    # Find runs of consecutive all-caps words (2+ chars each)
    consecutive = 0
    max_run = 0
    for word in words:
        # Strip punctuation for check
        clean = re.sub(r"[^\w]", "", word)
        if len(clean) >= 2 and clean.isupper():
            consecutive += 1
            max_run = max(max_run, consecutive)
        else:
            consecutive = 0

    if max_run >= 3:
        return [f"All-caps sequence: {max_run} consecutive all-caps words"], deduction

    return [], 0.0


def spam_obfuscation(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Detect character obfuscation (leet-speak substitution)."""
    text = _extract_text(raw_html)
    deduction = float(config.params.get("deduction_obfuscation", 0.15) if config else 0.15)

    # Find words containing digit substitutions and decode them
    issues: list[str] = []
    # Match words that have a mix of letters and digits (potential leet-speak)
    leet_candidates = re.findall(r"\b[a-zA-Z0-9@$]{3,}\b", text)

    for candidate in leet_candidates:
        if not _LEET_DECODE.search(candidate):
            continue
        # Decode leet-speak
        decoded = ""
        for ch in candidate.lower():
            decoded += _LEET_MAP.get(ch) or ch
        if decoded in _KNOWN_LEET_WORDS and decoded != candidate.lower():
            issues.append(f"Obfuscated word: '{candidate}' (decoded: '{decoded}')")

    if issues:
        return issues[:5], deduction

    return [], 0.0


def spam_score_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — no deduction."""
    triggers = _load_spam_triggers()
    text = _extract_text(raw_html)

    matched_count = 0
    categories: Counter[str] = Counter()

    for trigger in triggers:
        phrase = str(trigger.get("phrase", ""))
        category = str(trigger.get("category", "unknown"))
        pattern = _get_trigger_pattern(phrase)
        if pattern.search(text):
            matched_count += 1
            categories[category] += 1

    if matched_count == 0:
        return [], 0.0

    cat_breakdown = ", ".join(f"{cat}: {count}" for cat, count in categories.most_common())
    return [f"Triggers matched: {matched_count}/{len(triggers)} ({cat_breakdown})"], 0.0


register_custom_check("spam_trigger_scan", spam_trigger_scan)
register_custom_check("spam_subject_triggers", spam_subject_triggers)
register_custom_check("spam_excessive_punctuation", spam_excessive_punctuation)
register_custom_check("spam_all_caps_words", spam_all_caps_words)
register_custom_check("spam_obfuscation", spam_obfuscation)
register_custom_check("spam_score_summary", spam_score_summary)
