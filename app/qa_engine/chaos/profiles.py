# pyright: reportUnnecessaryIsInstance=false
"""Chaos profiles simulating real-world email client degradations."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag


@dataclass(frozen=True)
class ChaosProfile:
    """A named set of HTML transformations simulating a client behavior."""

    name: str
    description: str
    transformations: tuple[Callable[[str], str], ...] = field(default_factory=tuple)

    def apply(self, html: str) -> str:
        """Apply all transformations sequentially."""
        result = html
        for transform in self.transformations:
            result = transform(result)
        return result


# --- Transformation functions (pure, deterministic) ---


def _strip_style_blocks(html: str) -> str:
    """Remove all <style> and <link rel='stylesheet'> elements (Gmail behavior)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("style"):
        tag.decompose()
    for tag in soup.find_all("link"):
        if isinstance(tag, Tag) and tag.get("rel") == ["stylesheet"]:
            tag.decompose()
    return str(soup)


def _block_images(html: str) -> str:
    """Replace all <img> src with transparent 1x1 GIF (image-blocked behavior)."""
    soup = BeautifulSoup(html, "html.parser")
    transparent_gif = (
        "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    )
    for img in soup.find_all("img"):
        if isinstance(img, Tag):
            img["src"] = transparent_gif
    return str(soup)


def _inject_dark_mode(html: str) -> str:
    """Inject dark mode inversion CSS and data attributes (Outlook/Apple Mail behavior)."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if isinstance(body, Tag):
        body["data-ogsc"] = ""
        body["data-ogsb"] = ""
        existing_style = body.get("style", "")
        body["style"] = f"{existing_style}; filter: invert(1) hue-rotate(180deg);"
    return str(soup)


def _strip_flexbox_grid(html: str) -> str:
    """Strip flexbox/grid/custom properties from inline styles (Outlook Word engine)."""
    soup = BeautifulSoup(html, "html.parser")
    flex_grid_re = re.compile(
        r"(display\s*:\s*(flex|grid|inline-flex|inline-grid)"
        r"|flex[-\w]*\s*:[^;]+"
        r"|grid[-\w]*\s*:[^;]+"
        r"|--[\w-]+\s*:[^;]+"
        r"|var\s*\([^)]+\))",
        re.IGNORECASE,
    )
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and tag.get("style"):
            cleaned = flex_grid_re.sub("", str(tag["style"]))
            # Remove leftover empty semicolons
            cleaned = re.sub(r";\s*;", ";", cleaned).strip("; ")
            if cleaned:
                tag["style"] = cleaned
            else:
                del tag["style"]
    return str(soup)


def _clip_at_102kb(html: str) -> str:
    """Truncate HTML at 102,400 bytes (Gmail clipping behavior).

    Ensures truncation doesn't cut mid-tag by finding the last complete
    tag boundary before the limit.
    """
    encoded = html.encode("utf-8")
    if len(encoded) <= 102_400:
        return html
    # Find the last '>' before the 102KB boundary
    truncated = encoded[:102_400]
    last_gt = truncated.rfind(b">")
    if last_gt > 0:
        truncated = truncated[: last_gt + 1]
    return truncated.decode("utf-8", errors="ignore")


def _inject_narrow_viewport(html: str) -> str:
    """Inject max-width: 375px on body (mobile narrow viewport)."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if isinstance(body, Tag):
        existing_style = body.get("style", "")
        body["style"] = f"{existing_style}; max-width: 375px; overflow: hidden;"
    return str(soup)


def _strip_classes(html: str) -> str:
    """Remove all class attributes (security-focused email clients)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        if isinstance(tag, Tag) and tag.get("class"):
            del tag["class"]
    return str(soup)


def _strip_media_queries(html: str) -> str:
    """Remove all @media rules from <style> blocks and inline styles."""
    # Remove @media blocks from <style> tags
    media_block_re = re.compile(r"@media\s*[^{]*\{(?:[^{}]*\{[^}]*\})*[^}]*\}", re.IGNORECASE)
    soup = BeautifulSoup(html, "html.parser")
    for style_tag in soup.find_all("style"):
        if isinstance(style_tag, Tag) and style_tag.string:
            style_tag.string = media_block_re.sub("", style_tag.string)
    return str(soup)


# --- Pre-built profiles ---

GMAIL_STYLE_STRIP = ChaosProfile(
    name="gmail_style_strip",
    description="Removes all <style> blocks and stylesheet links (Gmail web behavior)",
    transformations=(_strip_style_blocks,),
)

IMAGE_BLOCKED = ChaosProfile(
    name="image_blocked",
    description="Replaces all image sources with transparent 1x1 GIF (image blocking)",
    transformations=(_block_images,),
)

DARK_MODE_INVERSION = ChaosProfile(
    name="dark_mode_inversion",
    description="Injects CSS filter inversion and data-ogsc/data-ogsb attributes (dark mode)",
    transformations=(_inject_dark_mode,),
)

OUTLOOK_WORD_ENGINE = ChaosProfile(
    name="outlook_word_engine",
    description="Strips flexbox, grid, and CSS custom properties (Outlook Word rendering engine)",
    transformations=(_strip_flexbox_grid,),
)

GMAIL_CLIPPING = ChaosProfile(
    name="gmail_clipping",
    description="Truncates HTML at 102KB boundary without cutting mid-tag (Gmail clipping)",
    transformations=(_clip_at_102kb,),
)

MOBILE_NARROW = ChaosProfile(
    name="mobile_narrow",
    description="Injects max-width: 375px on body element (mobile viewport)",
    transformations=(_inject_narrow_viewport,),
)

CLASS_STRIP = ChaosProfile(
    name="class_strip",
    description="Removes all class attributes (security-focused email clients)",
    transformations=(_strip_classes,),
)

MEDIA_QUERY_STRIP = ChaosProfile(
    name="media_query_strip",
    description="Removes all @media rules from style blocks (non-responsive clients)",
    transformations=(_strip_media_queries,),
)

# Registry of all profiles by name
PROFILES: dict[str, ChaosProfile] = {
    p.name: p
    for p in [
        GMAIL_STYLE_STRIP,
        IMAGE_BLOCKED,
        DARK_MODE_INVERSION,
        OUTLOOK_WORD_ENGINE,
        GMAIL_CLIPPING,
        MOBILE_NARROW,
        CLASS_STRIP,
        MEDIA_QUERY_STRIP,
    ]
}
