# ruff: noqa: ARG001
"""Image optimization custom checks (domain split from custom_checks.py)."""

from __future__ import annotations

from lxml.html import HtmlElement

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.image_analyzer import BANNED_FORMATS
from app.qa_engine.image_analyzer import get_cached_result as get_img_cached_result
from app.qa_engine.rule_engine import register_custom_check

# ---------------------------------------------------------------------------
# Image Optimization check functions
# ---------------------------------------------------------------------------


def _img_param(config: QACheckConfig | None, key: str, default: float) -> float:
    """Resolve image optimization config parameter."""
    if config and key in config.params:
        return float(config.params[key])
    return default


def image_missing_dimensions(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images missing width and/or height attributes (excluding tracking pixels)."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_dimensions", 0.05)
    cap = int(_img_param(config, "max_dimension_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if img.width is None or img.height is None:
            count += 1
            if len(issues) < cap:
                missing: list[str] = []
                if img.width is None:
                    missing.append("width")
                if img.height is None:
                    missing.append("height")
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image missing {', '.join(missing)}: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images with missing dimensions")
    return issues, round(count * deduction, 4)


def image_missing_alt(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-decorative images missing alt attribute entirely."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_alt", 0.05)
    cap = int(_img_param(config, "max_alt_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if img.alt is None:  # None = attribute absent (not empty string)
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image missing alt attribute: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without alt")
    return issues, round(count * deduction, 4)


def image_empty_src(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images with empty or missing src."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_empty_src", 0.10)
    cap = int(_img_param(config, "max_src_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if not img.src:
            count += 1
            if len(issues) < cap:
                issues.append("Image with empty or missing src attribute")
    if count > cap:
        issues.append(f"... and {count - cap} more images with empty src")
    return issues, round(count * deduction, 4)


def image_banned_format(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag BMP/TIFF images."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_banned_format", 0.10)
    cap = int(_img_param(config, "max_format_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.format in BANNED_FORMATS:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"{img.format.value.upper()} format: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more banned format images")
    return issues, round(count * deduction, 4)


def image_data_uri_oversize(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag data URIs exceeding size threshold."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_data_uri_oversize", 0.10)
    threshold = int(_img_param(config, "data_uri_max_bytes", 3072))  # 3KB
    cap = int(_img_param(config, "max_data_uri_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_data_uri and img.data_uri_bytes > threshold:
            count += 1
            if len(issues) < cap:
                kb = round(img.data_uri_bytes / 1024, 1)
                issues.append(f"Data URI image {kb}KB exceeds {threshold // 1024}KB threshold")
    if count > cap:
        issues.append(f"... and {count - cap} more oversized data URI images")
    return issues, round(count * deduction, 4)


def image_invalid_dimension_value(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag non-numeric dimension values (e.g., '100px', 'auto')."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_invalid_dimension", 0.03)
    cap = int(_img_param(config, "max_dimension_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        for attr_name, attr_val in [("width", img.width), ("height", img.height)]:
            if attr_val is not None:
                stripped = attr_val.strip()
                if stripped and not stripped.isdigit():
                    count += 1
                    if len(issues) < cap:
                        src_display = img.src[:50] + "..." if len(img.src) > 50 else img.src
                        issues.append(f'Invalid {attr_name}="{attr_val}" on: {src_display}')
    if count > cap:
        issues.append(f"... and {count - cap} more invalid dimension values")
    return issues, round(count * deduction, 4)


def image_tracking_pixel_visible(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag tracking pixels that are visible to screen readers."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_tracking_pixel", 0.03)
    cap = int(_img_param(config, "max_tracking_issues_reported", 3))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if not img.is_tracking_pixel:
            continue
        problems: list[str] = []
        if img.alt is None or img.alt != "":
            problems.append('needs alt=""')
        if not img.has_aria_hidden:
            problems.append('needs aria-hidden="true"')
        if problems:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:50] + "..." if len(img.src) > 50 else img.src
                issues.append(f"Tracking pixel ({', '.join(problems)}): {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more tracking pixel issues")
    return issues, round(count * deduction, 4)


def image_missing_border_zero(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images inside <a> tags without border='0'."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_border", 0.03)
    cap = int(_img_param(config, "max_border_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_inside_link and not img.has_border_zero:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Linked image without border='0': {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without border='0'")
    return issues, round(count * deduction, 4)


def image_missing_display_block(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Flag images without display:block in inline style."""
    result = get_img_cached_result(raw_html)
    deduction = _img_param(config, "deduction_missing_display_block", 0.02)
    cap = int(_img_param(config, "max_display_issues_reported", 5))
    issues: list[str] = []
    count = 0
    for img in result.images:
        if img.is_tracking_pixel:
            continue
        if not img.has_display_block:
            count += 1
            if len(issues) < cap:
                src_display = img.src[:60] + "..." if len(img.src) > 60 else img.src
                issues.append(f"Image without display:block: {src_display}")
    if count > cap:
        issues.append(f"... and {count - cap} more images without display:block")
    return issues, round(count * deduction, 4)


def image_summary(
    doc: HtmlElement,
    raw_html: str,
    config: QACheckConfig | None,
) -> tuple[list[str], float]:
    """Informational summary of image analysis."""
    result = get_img_cached_result(raw_html)
    if result.total_count == 0:
        return ["Images: none found"], 0.0

    parts = [f"Images: {result.total_count} total"]
    if result.tracking_pixel_count:
        parts.append(f"{result.tracking_pixel_count} tracking pixel(s)")
    if result.format_distribution:
        fmt_str = ", ".join(f"{k}: {v}" for k, v in sorted(result.format_distribution.items()))
        parts.append(f"formats: {fmt_str}")
    parts.append(f"{result.images_with_alt}/{result.total_count} with alt text")
    return ["; ".join(parts)], 0.0


# Register image optimization custom checks
register_custom_check("image_missing_dimensions", image_missing_dimensions)
register_custom_check("image_missing_alt", image_missing_alt)
register_custom_check("image_empty_src", image_empty_src)
register_custom_check("image_banned_format", image_banned_format)
register_custom_check("image_data_uri_oversize", image_data_uri_oversize)
register_custom_check("image_invalid_dimension_value", image_invalid_dimension_value)
register_custom_check("image_tracking_pixel_visible", image_tracking_pixel_visible)
register_custom_check("image_missing_border_zero", image_missing_border_zero)
register_custom_check("image_missing_display_block", image_missing_display_block)
register_custom_check("image_summary", image_summary)
