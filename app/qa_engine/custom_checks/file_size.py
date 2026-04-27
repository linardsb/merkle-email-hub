# ruff: noqa: ARG001
"""File size custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.file_size_analyzer import get_cached_result as get_fs_cached_result
from app.qa_engine.rule_engine import register_custom_check

# ─── File Size Custom Checks ─── (delegates to file_size_analyzer module)


def _fs_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve file size config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def file_size_gmail_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Gmail 102KB clipping threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "gmail_threshold_kb", 102.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_gmail_clip", 0.30)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Gmail {threshold:.0f}KB clipping threshold"
        ], deduction
    return [], 0.0


def file_size_outlook_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Outlook 100KB performance threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "outlook_threshold_kb", 100.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_outlook_perf", 0.20)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Outlook {threshold:.0f}KB performance threshold"
        ], deduction
    return [], 0.0


def file_size_yahoo_threshold(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Yahoo 75KB conservative threshold."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "yahoo_threshold_kb", 75.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_yahoo_clip", 0.10)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Yahoo {threshold:.0f}KB threshold"
        ], deduction
    return [], 0.0


def file_size_braze_limit(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check HTML size against Braze 100KB hard limit."""
    result = get_fs_cached_result(raw_html)
    threshold = _fs_param(config, "braze_threshold_kb", 100.0)
    if result.raw_size_kb > threshold:
        deduction = _fs_param(config, "deduction_braze_limit", 0.15)
        return [
            f"HTML is {result.raw_size_kb:.1f}KB — exceeds Braze {threshold:.0f}KB hard limit"
        ], deduction
    return [], 0.0


def file_size_inline_css_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check inline CSS does not exceed configured percentage of total size."""
    result = get_fs_cached_result(raw_html)
    max_pct = _fs_param(config, "inline_css_max_pct", 40.0)
    if result.breakdown.inline_styles_pct > max_pct:
        deduction = _fs_param(config, "deduction_inline_css_bloat", 0.05)
        return [
            f"Inline styles are {result.breakdown.inline_styles_pct:.0f}% of HTML "
            f"({result.breakdown.inline_styles_bytes / 1024:.1f}KB) — exceeds {max_pct:.0f}% threshold"
        ], deduction
    return [], 0.0


def file_size_mso_ratio(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check MSO conditional blocks do not exceed configured percentage."""
    result = get_fs_cached_result(raw_html)
    max_pct = _fs_param(config, "mso_conditional_max_pct", 25.0)
    if result.breakdown.mso_conditional_pct > max_pct:
        deduction = _fs_param(config, "deduction_mso_bloat", 0.05)
        return [
            f"MSO conditionals are {result.breakdown.mso_conditional_pct:.0f}% of HTML "
            f"({result.breakdown.mso_conditional_bytes / 1024:.1f}KB) — exceeds {max_pct:.0f}% threshold"
        ], deduction
    return [], 0.0


def file_size_gzip_efficiency(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Check gzip compression achieves minimum reduction (skip tiny emails)."""
    result = get_fs_cached_result(raw_html)
    min_reduction = _fs_param(config, "gzip_min_reduction_pct", 50.0)
    reduction_pct = (1.0 - result.compression_ratio) * 100
    if reduction_pct < min_reduction and result.raw_size_kb > 20:
        deduction = _fs_param(config, "deduction_poor_gzip", 0.05)
        return [
            f"Gzip compression only reduces size by {reduction_pct:.0f}% "
            f"({result.raw_size_kb:.1f}KB → {result.gzip_size_kb:.1f}KB) — "
            f"may contain base64-encoded data or large inline assets"
        ], deduction
    return [], 0.0


def file_size_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary — always 0 deduction."""
    result = get_fs_cached_result(raw_html)
    b = result.breakdown
    summary = (
        f"Raw: {result.raw_size_kb:.1f}KB | Gzip: {result.gzip_size_kb:.1f}KB "
        f"({(1 - result.compression_ratio) * 100:.0f}% reduction) | "
        f"Breakdown: styles {b.inline_styles_pct:.0f}%/{b.head_styles_pct:.0f}%, "
        f"MSO {b.mso_conditional_pct:.0f}%, "
        f"images {b.image_tag_bytes / max(b.total_bytes, 1) * 100:.0f}%"
    )
    return [summary], 0.0


register_custom_check("file_size_gmail_threshold", file_size_gmail_threshold)
register_custom_check("file_size_outlook_threshold", file_size_outlook_threshold)
register_custom_check("file_size_yahoo_threshold", file_size_yahoo_threshold)
register_custom_check("file_size_braze_limit", file_size_braze_limit)
register_custom_check("file_size_inline_css_ratio", file_size_inline_css_ratio)
register_custom_check("file_size_mso_ratio", file_size_mso_ratio)
register_custom_check("file_size_gzip_efficiency", file_size_gzip_efficiency)
register_custom_check("file_size_summary", file_size_summary)
