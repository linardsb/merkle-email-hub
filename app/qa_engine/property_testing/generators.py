"""Hypothesis strategies and deterministic generators for random email HTML."""

from __future__ import annotations

import random as random_mod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

SECTION_TYPES = (
    "hero",
    "content",
    "cta",
    "footer",
    "navigation",
    "divider",
    "image_row",
    "social",
)
FONT_FAMILIES = (
    "Arial, sans-serif",
    "Georgia, serif",
    "Helvetica, Arial, sans-serif",
    "'Trebuchet MS', sans-serif",
)


@dataclass(frozen=True)
class EmailConfig:
    """Configuration for a generated email."""

    section_count: int
    section_types: tuple[str, ...]
    content_lengths: tuple[int, ...]
    font_family: str
    primary_color: str
    background_color: str
    text_color: str
    image_count: int
    image_widths: tuple[int, ...]
    table_nesting_depth: int
    has_mso_conditionals: bool
    has_dark_mode: bool
    dark_mode_complete: bool
    link_count: int
    include_javascript_links: bool
    include_empty_alt: bool
    target_size_kb: int


def _hex_colors() -> SearchStrategy[str]:
    """Strategy producing valid hex color strings."""
    from hypothesis import strategies as st

    return st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True)


def email_configs() -> SearchStrategy[EmailConfig]:
    """Strategy producing random email configurations."""
    from hypothesis import strategies as st

    return st.builds(
        EmailConfig,
        section_count=st.integers(min_value=1, max_value=15),
        section_types=st.lists(st.sampled_from(SECTION_TYPES), min_size=1, max_size=15).map(tuple),
        content_lengths=st.lists(
            st.integers(min_value=10, max_value=2000), min_size=1, max_size=15
        ).map(tuple),
        font_family=st.sampled_from(FONT_FAMILIES),
        primary_color=_hex_colors(),
        background_color=_hex_colors(),
        text_color=_hex_colors(),
        image_count=st.integers(min_value=0, max_value=10),
        image_widths=st.lists(
            st.integers(min_value=50, max_value=800), min_size=0, max_size=10
        ).map(tuple),
        table_nesting_depth=st.integers(min_value=0, max_value=12),
        has_mso_conditionals=st.booleans(),
        has_dark_mode=st.booleans(),
        dark_mode_complete=st.booleans(),
        link_count=st.integers(min_value=0, max_value=20),
        include_javascript_links=st.booleans(),
        include_empty_alt=st.booleans(),
        target_size_kb=st.integers(min_value=5, max_value=150),
    )


HEX_CHARS = "0123456789abcdef"


def _random_hex_color(rng: random_mod.Random) -> str:
    """Generate a random hex color using the given RNG."""
    return "#" + "".join(rng.choice(HEX_CHARS) for _ in range(6))


def random_email_config(rng: random_mod.Random) -> EmailConfig:
    """Generate a deterministic random email config using the given RNG."""
    section_count = rng.randint(1, 15)
    image_count = rng.randint(0, 10)
    link_count = rng.randint(0, 20)
    return EmailConfig(
        section_count=section_count,
        section_types=tuple(rng.choice(SECTION_TYPES) for _ in range(rng.randint(1, 15))),
        content_lengths=tuple(rng.randint(10, 2000) for _ in range(rng.randint(1, 15))),
        font_family=rng.choice(FONT_FAMILIES),
        primary_color=_random_hex_color(rng),
        background_color=_random_hex_color(rng),
        text_color=_random_hex_color(rng),
        image_count=image_count,
        image_widths=tuple(rng.randint(50, 800) for _ in range(rng.randint(0, 10))),
        table_nesting_depth=rng.randint(0, 12),
        has_mso_conditionals=rng.choice([True, False]),
        has_dark_mode=rng.choice([True, False]),
        dark_mode_complete=rng.choice([True, False]),
        link_count=link_count,
        include_javascript_links=rng.choice([True, False]),
        include_empty_alt=rng.choice([True, False]),
        target_size_kb=rng.randint(5, 150),
    )


def _build_sections(config: EmailConfig) -> str:
    """Build section HTML with table nesting."""
    parts: list[str] = []
    depth = min(config.table_nesting_depth, config.section_count)
    for i in range(depth):
        content_len = config.content_lengths[i] if i < len(config.content_lengths) else 100
        content = "L" * content_len
        parts.append(
            f'<table role="presentation" width="600"><tr><td '
            f'style="color:{config.text_color}; background-color:{config.background_color};">'
        )
        parts.append(f"<p>{content}</p>")
    # Close tables in reverse
    for _ in range(depth):
        parts.append("</td></tr></table>")
    # Remaining sections (flat)
    for i in range(depth, config.section_count):
        content_len = config.content_lengths[i] if i < len(config.content_lengths) else 100
        content = "L" * content_len
        parts.append('<table role="presentation" width="600"><tr><td>')
        parts.append(f"<p>{content}</p>")
        parts.append("</td></tr></table>")
    return "\n".join(parts)


def build_email(config: EmailConfig) -> str:
    """Build synthetic email HTML from configuration."""
    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append("<title>Test Email</title>")

    # Dark mode support
    if config.has_dark_mode:
        if config.dark_mode_complete:
            parts.append('<meta name="color-scheme" content="light dark">')
        parts.append("<style>")
        if config.dark_mode_complete:
            parts.append("@media (prefers-color-scheme: dark) {")
            parts.append("  body { background-color: #1a1a2e; color: #ffffff; }")
            parts.append("}")
        else:
            # Incomplete — only dark, no light counterpart in @media
            parts.append("@media (prefers-color-scheme: dark) {")
            parts.append("  body { background-color: #1a1a2e; }")
            parts.append("}")
        parts.append("</style>")

    parts.append("</head>")
    parts.append(
        f'<body style="background-color:{config.background_color}; '
        f'color:{config.text_color}; font-family:{config.font_family};">'
    )

    # MSO conditionals
    if config.has_mso_conditionals:
        parts.append("<!--[if mso]>")
        parts.append('<table role="presentation" width="600"><tr><td>')
        parts.append("<![endif]-->")

    # Sections with nested tables
    parts.append(_build_sections(config))

    # Images
    for i in range(config.image_count):
        width = config.image_widths[i] if i < len(config.image_widths) else 300
        alt = "" if config.include_empty_alt and i == 0 else f"Image {i + 1}"
        parts.append(
            f'<img src="https://example.com/img{i}.png" width="{width}" '
            f'alt="{alt}" style="width:{width}px;">'
        )

    # Links
    for i in range(config.link_count):
        if config.include_javascript_links and i == 0:
            parts.append('<a href="javascript:void(0)">Click</a>')
        else:
            parts.append(f'<a href="https://example.com/link{i}">Link {i}</a>')

    # Close MSO
    if config.has_mso_conditionals:
        parts.append("<!--[if mso]>")
        parts.append("</td></tr></table>")
        parts.append("<![endif]-->")

    parts.append("</body></html>")

    html = "\n".join(parts)

    # Pad to target size if needed
    if config.target_size_kb > 0:
        target_bytes = config.target_size_kb * 1024
        current = len(html.encode("utf-8"))
        if current < target_bytes:
            pad_len = target_bytes - current - 20
            if pad_len > 0:
                padding = "<!-- padding " + "x" * pad_len + " -->"
                html = html.replace("</body>", padding + "\n</body>")

    return html
