"""Deterministic post-processing for Accessibility alt text quality.

Validates alt text on <img> tags: rejects generic terms, single-word alts,
filename patterns, and checks length bounds for content images.
"""

import re
from dataclasses import dataclass

from lxml import html as lxml_html

# Generic alt text terms that are worse than empty alt (clutter screen readers)
_GENERIC_TERMS: frozenset[str] = frozenset(
    {
        "image",
        "photo",
        "picture",
        "graphic",
        "icon",
        "button",
        "logo",
        "banner",
        "img",
        "pic",
        "screenshot",
        "thumbnail",
        "untitled",
        "placeholder",
        "default",
        "no description",
    }
)

# Prefixes the agent should never use (screen readers already say "image")
_BAD_PREFIXES: tuple[str, ...] = (
    "image of",
    "photo of",
    "picture of",
    "graphic of",
    "icon of",
    "an image",
    "a photo",
    "a picture",
)

# Patterns indicating a filename was used as alt text
_FILENAME_PATTERN = re.compile(r"^[\w-]+\.(jpg|jpeg|png|gif|svg|webp|bmp|avif)$", re.IGNORECASE)

# Decorative image indicators — checked against the filename stem only.
# Each keyword must be a standalone segment (split on - or _) or the
# entire stem, to avoid false positives like "cross-border-shopping.jpg".
_DECORATIVE_KEYWORDS: frozenset[str] = frozenset(
    {
        "spacer",
        "pixel",
        "tracking",
        "1x1",
        "blank",
        "divider",
        "border",
        "separator",
        "shim",
    }
)

# Pre-compiled regex to split a filename stem into segments
_STEM_SPLIT_RE = re.compile(r"[-_]")

# Content image min/max word count
_MIN_CONTENT_WORDS = 2
_MAX_CONTENT_WORDS = 25  # ~125 chars


@dataclass(frozen=True)
class AltTextWarning:
    """A single alt text quality issue."""

    img_src: str
    issue: str
    severity: str  # "error" | "warning"


@dataclass(frozen=True)
class AltTextAnalysis:
    """Result of alt text quality analysis on an HTML document."""

    warnings: tuple[AltTextWarning, ...]
    total_images: int
    images_with_alt: int
    decorative_images: int
    content_images: int


def _is_likely_decorative(src: str) -> bool:
    """Check if image source suggests a decorative/spacer image.

    Extracts the filename from the path, strips the extension, splits into
    segments on ``-`` and ``_``, and checks whether the **first or last**
    segment is a known decorative keyword.  Only checking boundary segments
    avoids false positives on compound names like "cross-border-shopping.jpg"
    where a keyword appears in the middle.
    """
    # Extract filename from path (handles URLs and local paths)
    filename = src.rsplit("/", 1)[-1]
    # Strip extension
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    # Check first and last segments only
    segments = _STEM_SPLIT_RE.split(stem.lower())
    boundary: set[str] = {segments[0], segments[-1]} if segments else set()
    return bool(_DECORATIVE_KEYWORDS & boundary)


def _is_tracking_pixel(element: lxml_html.HtmlElement) -> bool:
    """Check if image is a tracking pixel (1x1 or hidden)."""
    w = element.get("width", "")
    h = element.get("height", "")
    style = element.get("style", "").lower()
    if w == "1" and h == "1":
        return True
    if "display:none" in style or "display: none" in style:
        return True
    return False


def validate_alt_text(html_content: str) -> AltTextAnalysis:
    """Validate alt text quality on all <img> tags in the HTML.

    Returns an AltTextAnalysis with warnings for each quality issue found.
    """
    warnings: list[AltTextWarning] = []

    try:
        doc = lxml_html.fromstring(html_content)
    except Exception:
        return AltTextAnalysis(
            warnings=(),
            total_images=0,
            images_with_alt=0,
            decorative_images=0,
            content_images=0,
        )

    total = 0
    with_alt = 0
    decorative_count = 0
    content_count = 0

    for img in doc.iter("img"):
        total += 1
        src = img.get("src", "unknown")
        alt = img.get("alt")

        if alt is None:
            # Missing alt attribute entirely
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue="missing alt attribute",
                    severity="error",
                )
            )
            continue

        with_alt += 1
        alt_stripped = alt.strip()
        is_decorative = _is_likely_decorative(src) or _is_tracking_pixel(img)

        if is_decorative:
            decorative_count += 1
            # Decorative images should have alt=""
            if alt_stripped:
                warnings.append(
                    AltTextWarning(
                        img_src=src,
                        issue=f'decorative image should have alt="" but has alt="{alt_stripped[:50]}"',
                        severity="warning",
                    )
                )
            continue

        # Content/functional image
        content_count += 1

        if not alt_stripped:
            # Empty alt on non-decorative image
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue='content image has empty alt="" — needs descriptive text',
                    severity="error",
                )
            )
            continue

        alt_lower = alt_stripped.lower()

        # Check for generic terms
        if alt_lower in _GENERIC_TERMS:
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue=f'generic alt text "{alt_stripped}" — describe the image content',
                    severity="error",
                )
            )
            continue

        # Check for bad prefixes
        for prefix in _BAD_PREFIXES:
            if alt_lower.startswith(prefix):
                warnings.append(
                    AltTextWarning(
                        img_src=src,
                        issue=f'alt text starts with "{prefix}" — screen readers already announce "image"',
                        severity="warning",
                    )
                )
                break

        # Check for filename as alt
        if _FILENAME_PATTERN.match(alt_stripped):
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue=f'filename "{alt_stripped}" used as alt text — describe the content',
                    severity="error",
                )
            )
            continue

        # Check word count bounds
        word_count = len(alt_stripped.split())
        if word_count < _MIN_CONTENT_WORDS:
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue=f'single-word alt "{alt_stripped}" — use 2-25 words for content images',
                    severity="warning",
                )
            )
        elif word_count > _MAX_CONTENT_WORDS:
            warnings.append(
                AltTextWarning(
                    img_src=src,
                    issue=f"alt text too long ({word_count} words) — keep under 25 words (~125 chars)",
                    severity="warning",
                )
            )

    return AltTextAnalysis(
        warnings=tuple(warnings),
        total_images=total,
        images_with_alt=with_alt,
        decorative_images=decorative_count,
        content_images=content_count,
    )


def format_alt_text_warnings(html_content: str) -> list[str]:
    """Run alt text validation and return formatted warning strings.

    This is the main entry point called by AccessibilityService._post_process().
    """
    analysis = validate_alt_text(html_content)
    formatted: list[str] = []

    for w in analysis.warnings:
        formatted.append(f"[{w.severity}] alt_text({w.img_src}): {w.issue}")

    if analysis.total_images > 0 and analysis.images_with_alt < analysis.total_images:
        missing = analysis.total_images - analysis.images_with_alt
        formatted.insert(
            0, f"[error] {missing}/{analysis.total_images} images missing alt attribute"
        )

    return formatted
