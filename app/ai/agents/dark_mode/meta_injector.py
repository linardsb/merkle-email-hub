"""Deterministic meta tag injector for dark mode email HTML.

Post-generation safety net: programmatically injects missing dark mode
meta tags that the LLM frequently omits (~50% failure rate in evals).

Reuses the existing dark_mode_parser.validate_dark_mode() for detection,
then performs surgical string insertion before </head>.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger
from app.qa_engine.dark_mode_parser import validate_dark_mode

logger = get_logger(__name__)

# Meta tags to inject (order matters — color-scheme first per spec)
_COLOR_SCHEME_META = '<meta name="color-scheme" content="light dark">'
_SUPPORTED_META = '<meta name="supported-color-schemes" content="light dark">'

# Pattern to find </head> insertion point (case-insensitive)
_HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)


@dataclass(frozen=True)
class MetaInjectionResult:
    """Result of deterministic meta tag injection."""

    html: str
    injected_tags: tuple[str, ...] = ()
    was_modified: bool = False


def inject_missing_meta_tags(html: str) -> MetaInjectionResult:
    """Check for required dark mode meta tags and inject if missing.

    Uses validate_dark_mode() from the existing parser to detect missing
    tags, then inserts them before </head>. Does NOT modify HTML if both
    tags are already present.

    Args:
        html: Email HTML (post-extraction, post-sanitization).

    Returns:
        MetaInjectionResult with possibly-modified HTML and list of
        injected tag names.
    """
    if not html or not html.strip():
        return MetaInjectionResult(html=html)

    result = validate_dark_mode(html)
    meta = result.meta_tags

    tags_to_inject: list[str] = []
    tag_names: list[str] = []

    if not meta.has_color_scheme:
        tags_to_inject.append(_COLOR_SCHEME_META)
        tag_names.append("color-scheme")

    if not meta.has_supported_color_schemes:
        tags_to_inject.append(_SUPPORTED_META)
        tag_names.append("supported-color-schemes")

    if not tags_to_inject:
        return MetaInjectionResult(html=html)

    # Find </head> and inject before it
    head_match = _HEAD_CLOSE_RE.search(html)
    if not head_match:
        logger.warning(
            "dark_mode.meta_injector.no_head_close",
            missing_tags=tag_names,
        )
        return MetaInjectionResult(html=html)

    injection = "\n".join(tags_to_inject) + "\n"
    insert_pos = head_match.start()
    modified_html = html[:insert_pos] + injection + html[insert_pos:]

    logger.info(
        "dark_mode.meta_injector.tags_injected",
        injected=tag_names,
        count=len(tag_names),
    )

    return MetaInjectionResult(
        html=modified_html,
        injected_tags=tuple(tag_names),
        was_modified=True,
    )
