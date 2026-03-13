"""Standalone file size analyzer for email HTML.

Provides content breakdown by category (inline styles, head styles, MSO conditionals,
image tags, HTML structure, text content), gzip estimation, and multi-client threshold
evaluation. Pure functions operating on raw HTML string bytes — no lxml dependency.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from enum import StrEnum

from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Data Models ─────────────────────────────────────────────────────────────


class FileSizeCategory(StrEnum):
    """Content breakdown categories."""

    INLINE_STYLES = "inline_styles"
    HEAD_STYLES = "head_styles"
    MSO_CONDITIONALS = "mso_conditionals"
    IMAGE_TAGS = "image_tags"
    HTML_STRUCTURE = "html_structure"
    TEXT_CONTENT = "text_content"


class ClientThreshold(StrEnum):
    """Email client size thresholds."""

    YAHOO = "yahoo"
    OUTLOOK = "outlook"
    GMAIL = "gmail"
    BRAZE = "braze"


@dataclass(frozen=True)
class ContentBreakdown:
    """Byte breakdown by content category."""

    inline_styles_bytes: int
    head_styles_bytes: int
    mso_conditional_bytes: int
    image_tag_bytes: int
    html_structure_bytes: int
    text_content_bytes: int
    total_bytes: int

    @property
    def inline_styles_pct(self) -> float:
        return (self.inline_styles_bytes / max(self.total_bytes, 1)) * 100

    @property
    def mso_conditional_pct(self) -> float:
        return (self.mso_conditional_bytes / max(self.total_bytes, 1)) * 100

    @property
    def head_styles_pct(self) -> float:
        return (self.head_styles_bytes / max(self.total_bytes, 1)) * 100


@dataclass(frozen=True)
class FileSizeIssue:
    """Single file size validation issue."""

    category: str  # "client_threshold", "content_ratio", "gzip"
    message: str
    severity: str  # "error", "warning", "info"


@dataclass(frozen=True)
class FileSizeResult:
    """Complete file size analysis result."""

    raw_size_bytes: int
    raw_size_kb: float
    gzip_size_bytes: int
    gzip_size_kb: float
    compression_ratio: float  # 0.0-1.0 (lower = better compression)
    breakdown: ContentBreakdown
    exceeded_clients: list[str]
    issues: list[FileSizeIssue] = field(default_factory=lambda: list[FileSizeIssue]())


# ─── Regex Patterns ──────────────────────────────────────────────────────────

_RE_INLINE_STYLE = re.compile(r'\bstyle\s*=\s*"[^"]*"', re.IGNORECASE)
_RE_HEAD_STYLE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_RE_MSO_CONDITIONAL = re.compile(
    r"<!--\[if\s[^\]]*\]>.*?<!\[endif\]-->",
    re.IGNORECASE | re.DOTALL,
)
_RE_IMG_TAG = re.compile(r"<img\b[^>]*/?>", re.IGNORECASE)
_RE_HTML_TAG = re.compile(r"<[^>]+>")


# ─── Byte Measurement ────────────────────────────────────────────────────────


def _measure_raw_size(html: str) -> tuple[int, float]:
    """Return (bytes, kilobytes) of UTF-8 encoded HTML."""
    raw_bytes = len(html.encode("utf-8"))
    return raw_bytes, raw_bytes / 1024


def _measure_gzip_size(html: str) -> tuple[int, float, float]:
    """Return (gzip_bytes, gzip_kb, compression_ratio).

    Uses gzip.compress(level=6) — standard email server compression.
    """
    encoded = html.encode("utf-8")
    raw_bytes = len(encoded)
    compressed = gzip.compress(encoded, compresslevel=6)
    gzip_bytes = len(compressed)
    ratio = gzip_bytes / max(raw_bytes, 1)
    return gzip_bytes, gzip_bytes / 1024, ratio


# ─── Content Breakdown ───────────────────────────────────────────────────────


def _compute_breakdown(html: str, total_bytes: int) -> ContentBreakdown:
    """Categorise bytes across 6 content categories.

    Strategy: extract each category's raw text via regex, measure its UTF-8 byte length.
    Categories are extracted in priority order to avoid double-counting:
    1. MSO conditionals (remove from working copy)
    2. <style> blocks (remove from working copy)
    3. Inline style="" attributes (measure but don't remove — embedded in tags)
    4. <img> tags (measure full tag)
    5. Remaining HTML tags = html_structure
    6. Remaining text = text_content
    """
    working = html

    # 1. MSO conditionals — extract and remove
    mso_bytes = 0
    for match in _RE_MSO_CONDITIONAL.finditer(working):
        mso_bytes += len(match.group(0).encode("utf-8"))
    working = _RE_MSO_CONDITIONAL.sub("", working)

    # 2. <style> blocks — extract and remove
    head_style_bytes = 0
    for match in _RE_HEAD_STYLE.finditer(working):
        head_style_bytes += len(match.group(0).encode("utf-8"))
    working = _RE_HEAD_STYLE.sub("", working)

    # 3. Inline style="" — measure (from original minus MSO/style blocks)
    inline_style_bytes = 0
    for match in _RE_INLINE_STYLE.finditer(working):
        inline_style_bytes += len(match.group(0).encode("utf-8"))

    # 4. <img> tags — measure full tag
    img_bytes = 0
    for match in _RE_IMG_TAG.finditer(working):
        img_bytes += len(match.group(0).encode("utf-8"))

    # 5. Remaining HTML tags (excluding img already counted)
    working_no_img = _RE_IMG_TAG.sub("", working)
    html_structure_bytes = 0
    for match in _RE_HTML_TAG.finditer(working_no_img):
        html_structure_bytes += len(match.group(0).encode("utf-8"))

    # 6. Text content — everything that's not a tag
    text_only = _RE_HTML_TAG.sub("", working_no_img)
    text_bytes = len(text_only.encode("utf-8"))

    return ContentBreakdown(
        inline_styles_bytes=inline_style_bytes,
        head_styles_bytes=head_style_bytes,
        mso_conditional_bytes=mso_bytes,
        image_tag_bytes=img_bytes,
        html_structure_bytes=html_structure_bytes,
        text_content_bytes=text_bytes,
        total_bytes=total_bytes,
    )


# ─── Client Threshold Evaluation ─────────────────────────────────────────────

_CLIENT_THRESHOLDS: dict[str, int] = {
    "yahoo": 75,
    "outlook": 100,
    "gmail": 102,
    "braze": 100,
}


def _evaluate_thresholds(size_kb: float) -> list[str]:
    """Return list of client names whose thresholds are exceeded."""
    return [name for name, limit in _CLIENT_THRESHOLDS.items() if size_kb > limit]


# ─── Public API ──────────────────────────────────────────────────────────────


def analyze_file_size(html: str) -> FileSizeResult:
    """Analyze email HTML file size with content breakdown and gzip estimate."""
    raw_bytes, raw_kb = _measure_raw_size(html)
    gzip_bytes, gzip_kb, compression_ratio = _measure_gzip_size(html)
    breakdown = _compute_breakdown(html, raw_bytes)
    exceeded = _evaluate_thresholds(raw_kb)

    issues: list[FileSizeIssue] = []
    for client in exceeded:
        threshold = _CLIENT_THRESHOLDS[client]
        issues.append(
            FileSizeIssue(
                category="client_threshold",
                message=f"Exceeds {client} {threshold}KB threshold",
                severity="error" if client == "gmail" else "warning",
            )
        )

    logger.info(
        "qa_engine.file_size.analysis_completed",
        raw_kb=round(raw_kb, 1),
        gzip_kb=round(gzip_kb, 1),
        compression_ratio=round(compression_ratio, 3),
        exceeded_clients=exceeded,
    )

    return FileSizeResult(
        raw_size_bytes=raw_bytes,
        raw_size_kb=round(raw_kb, 2),
        gzip_size_bytes=gzip_bytes,
        gzip_size_kb=round(gzip_kb, 2),
        compression_ratio=round(compression_ratio, 4),
        breakdown=breakdown,
        exceeded_clients=exceeded,
        issues=issues,
    )


# ─── Caching ─────────────────────────────────────────────────────────────────

_cache: dict[int, FileSizeResult] = {}


def get_cached_result(html: str) -> FileSizeResult:
    """Return cached FileSizeResult, computing if not cached. Hash-based cache."""
    h = hash(html)
    if h not in _cache:
        _cache[h] = analyze_file_size(html)
    return _cache[h]


def clear_file_size_cache() -> None:
    """Clear the analysis cache. Call at start of each check run."""
    _cache.clear()
