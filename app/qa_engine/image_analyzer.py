"""Image analysis for email HTML — DOM-parsed image extraction and validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final
from urllib.parse import urlparse

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.core.logging import get_logger

logger = get_logger(__name__)


class ImageFormat(StrEnum):
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    SVG = "svg"
    BMP = "bmp"
    TIFF = "tiff"
    UNKNOWN = "unknown"


BANNED_FORMATS: Final[frozenset[ImageFormat]] = frozenset({ImageFormat.BMP, ImageFormat.TIFF})

# Extension → format mapping
_EXT_MAP: Final[dict[str, ImageFormat]] = {
    ".jpg": ImageFormat.JPEG,
    ".jpeg": ImageFormat.JPEG,
    ".png": ImageFormat.PNG,
    ".gif": ImageFormat.GIF,
    ".webp": ImageFormat.WEBP,
    ".svg": ImageFormat.SVG,
    ".bmp": ImageFormat.BMP,
    ".tiff": ImageFormat.TIFF,
    ".tif": ImageFormat.TIFF,
}

# data: URI MIME → format mapping
_MIME_MAP: Final[dict[str, ImageFormat]] = {
    "image/jpeg": ImageFormat.JPEG,
    "image/png": ImageFormat.PNG,
    "image/gif": ImageFormat.GIF,
    "image/webp": ImageFormat.WEBP,
    "image/svg+xml": ImageFormat.SVG,
    "image/bmp": ImageFormat.BMP,
    "image/tiff": ImageFormat.TIFF,
}

_DATA_URI_MIME_RE: Final[re.Pattern[str]] = re.compile(r"^data:(image/[^;,]+)")
_DISPLAY_BLOCK_RE: Final[re.Pattern[str]] = re.compile(r"display\s*:\s*block", re.IGNORECASE)
_TRACKING_SRC_PATTERNS: Final[tuple[str, ...]] = (
    "track",
    "pixel",
    "beacon",
    "open",
    "o.gif",
    "spacer.gif",
)


@dataclass(frozen=True)
class ImageInfo:
    """Parsed metadata for a single <img> element."""

    src: str
    alt: str | None  # None = attribute absent; "" = present but empty
    width: str | None  # Raw attribute value
    height: str | None  # Raw attribute value
    style: str  # Inline style string
    format: ImageFormat
    is_tracking_pixel: bool  # 1x1 dimensions or known tracking patterns
    is_inside_link: bool  # <a> ancestor
    has_border_zero: bool  # border="0" attribute
    has_display_block: bool  # display:block in inline style
    has_aria_hidden: bool  # aria-hidden="true"
    is_data_uri: bool
    data_uri_bytes: int  # 0 if not data URI


@dataclass(frozen=True)
class ImageAnalysisResult:
    """Complete image analysis for an HTML email."""

    images: tuple[ImageInfo, ...]
    total_count: int
    tracking_pixel_count: int
    format_distribution: dict[str, int]  # format name → count
    images_with_alt: int
    images_missing_alt: int
    images_missing_dimensions: int


def _detect_format(src: str) -> ImageFormat:
    """Detect image format from src URL or data URI."""
    if not src:
        return ImageFormat.UNKNOWN

    # Data URI — extract MIME type
    mime_match = _DATA_URI_MIME_RE.match(src)
    if mime_match:
        mime = mime_match.group(1).lower()
        return _MIME_MAP.get(mime, ImageFormat.UNKNOWN)

    # URL — extract extension from path
    try:
        parsed = urlparse(src)
        path = parsed.path.lower()
        for ext, fmt in _EXT_MAP.items():
            if path.endswith(ext):
                return fmt
    except Exception:  # noqa: S110
        pass

    return ImageFormat.UNKNOWN


def _strip_px(val: str | None) -> str | None:
    """Strip 'px' suffix from a dimension value for comparison."""
    if val is None:
        return None
    stripped = val.strip()
    if stripped.lower().endswith("px"):
        stripped = stripped[:-2].strip()
    return stripped


def _is_tracking_pixel(width: str | None, height: str | None, src: str) -> bool:
    """Detect tracking pixels by dimensions or known patterns."""
    # Check 1x1 dimensions
    w = _strip_px(width)
    h = _strip_px(height)
    if w == "1" and h == "1":
        return True
    if w == "0" and h == "0":
        return True

    # Known tracking src patterns
    src_lower = src.lower()
    return any(pattern in src_lower for pattern in _TRACKING_SRC_PATTERNS)


def _calc_data_uri_bytes(src: str) -> int:
    """Calculate approximate byte size of a data URI payload."""
    if not src.startswith("data:"):
        return 0

    # Find the data portion after the comma
    comma_idx = src.find(",")
    if comma_idx == -1:
        return 0

    payload = src[comma_idx + 1 :]

    # Check if base64 encoded
    header = src[:comma_idx].lower()
    if "base64" in header:
        # Base64: every 4 chars encode 3 bytes, minus padding
        padding = payload.count("=")
        return max(0, (len(payload) * 3) // 4 - padding)
    return len(payload.encode("utf-8", errors="replace"))


def _parse_image_element(img_el: HtmlElement) -> ImageInfo:
    """Extract all metadata from a single <img> element."""
    src = (img_el.get("src") or "").strip()
    alt = img_el.get("alt")  # None = absent, "" = empty
    width = img_el.get("width")
    height = img_el.get("height")
    style = img_el.get("style") or ""
    border = img_el.get("border") or ""
    aria_hidden = (img_el.get("aria-hidden") or "").lower()

    # Detect format
    fmt = _detect_format(src)

    # Check if inside <a> — walk up to 5 parents
    is_inside_link = False
    parent = img_el.getparent()
    for _ in range(5):
        if parent is None:
            break
        if parent.tag == "a":
            is_inside_link = True
            break
        parent = parent.getparent()

    # Style checks
    has_display_block = bool(_DISPLAY_BLOCK_RE.search(style))

    # Data URI
    is_data_uri = src.startswith("data:")
    data_uri_bytes = _calc_data_uri_bytes(src) if is_data_uri else 0

    return ImageInfo(
        src=src,
        alt=alt,
        width=width,
        height=height,
        style=style,
        format=fmt,
        is_tracking_pixel=_is_tracking_pixel(width, height, src),
        is_inside_link=is_inside_link,
        has_border_zero=border == "0",
        has_display_block=has_display_block,
        has_aria_hidden=aria_hidden == "true",
        is_data_uri=is_data_uri,
        data_uri_bytes=data_uri_bytes,
    )


def analyze_images(html: str) -> ImageAnalysisResult:
    """Analyze all images in an HTML email. Main entry point."""
    doc = lxml_html.document_fromstring(html)
    img_elements: list[HtmlElement] = doc.xpath("//img")
    images: list[ImageInfo] = []
    for img_el in img_elements:
        images.append(_parse_image_element(img_el))

    # Compute aggregates
    tracking = sum(1 for i in images if i.is_tracking_pixel)
    format_dist: dict[str, int] = {}
    for img in images:
        format_dist[img.format.value] = format_dist.get(img.format.value, 0) + 1
    with_alt = sum(1 for i in images if i.alt is not None)
    missing_alt = sum(1 for i in images if i.alt is None and not i.is_tracking_pixel)
    missing_dims = sum(1 for i in images if i.width is None or i.height is None)

    return ImageAnalysisResult(
        images=tuple(images),
        total_count=len(images),
        tracking_pixel_count=tracking,
        format_distribution=format_dist,
        images_with_alt=with_alt,
        images_missing_alt=missing_alt,
        images_missing_dimensions=missing_dims,
    )


# --- Caching ---

_cache: dict[str, ImageAnalysisResult] = {}


def get_cached_result(html: str) -> ImageAnalysisResult:
    """Get or compute image analysis result, cached by content hash."""
    key = hashlib.md5(html.encode()).hexdigest()  # noqa: S324
    if key not in _cache:
        _cache[key] = analyze_images(html)
    return _cache[key]


def clear_image_cache() -> None:
    """Clear the image analysis cache."""
    _cache.clear()
