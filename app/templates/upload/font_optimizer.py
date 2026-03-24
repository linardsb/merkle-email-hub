"""Email client font stack optimizer.

Ensures font stacks include appropriate fallbacks for each target email client,
and injects `mso-font-alt` declarations for Outlook targets.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger

logger = get_logger(__name__)

_INLINE_STYLE_RE = re.compile(r"""style\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.IGNORECASE)

_DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "email_client_fonts.yaml"


@lru_cache(maxsize=1)
def _load_font_data() -> dict[str, Any]:
    """Load email client font support data."""
    with _DATA_PATH.open() as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


class EmailClientFontOptimizer:
    """Optimizes font stacks for email client compatibility."""

    def __init__(self) -> None:
        data = _load_font_data()
        self._clients: dict[str, Any] = data.get("clients", {})
        self._fallback_map: dict[str, list[str]] = data.get("fallback_map", {})

    def optimize_font_stack(self, font_family: str, target_clients: list[str]) -> str:
        """Optimize a font-family stack for target email clients.

        Ensures the stack includes appropriate system fallbacks for clients
        that don't support web fonts.
        """
        fonts = self._parse_stack(font_family)
        if not fonts:
            return font_family

        primary = fonts[0].strip("'\"")
        fallbacks = self._fallback_map.get(primary)

        if not fallbacks:
            return font_family

        # Check if any target client needs system fonts
        needs_fallback = any(
            self._client_needs_fallback(client, primary) for client in target_clients
        )

        if not needs_fallback:
            return font_family

        # Merge fallbacks into existing stack (avoid duplicates)
        existing_lower = {f.strip().strip("'\"").lower() for f in fonts}
        merged = list(fonts)
        for fb in fallbacks:
            if fb.lower() not in existing_lower:
                # Insert before generic family (serif/sans-serif/monospace)
                insert_pos = len(merged)
                for i, f in enumerate(merged):
                    if f.strip().strip("'\"").lower() in ("serif", "sans-serif", "monospace"):
                        insert_pos = i
                        break
                merged.insert(insert_pos, fb)
                existing_lower.add(fb.lower())

        return ", ".join(merged)

    def get_mso_font_alt(self, font_family: str) -> str | None:
        """Get the mso-font-alt value for a font stack.

        Returns the first system-safe fallback, or None if not needed.
        """
        fonts = self._parse_stack(font_family)
        if not fonts:
            return None
        primary = fonts[0].strip("'\"")
        fallbacks = self._fallback_map.get(primary)
        if not fallbacks:
            return None
        # Return first non-generic fallback
        for fb in fallbacks:
            if fb.lower() not in ("serif", "sans-serif", "monospace"):
                return fb
        return None

    def inject_mso_font_alt(self, html: str, target_clients: list[str]) -> str:
        """Inject mso-font-alt into inline styles for Outlook targets.

        Only acts if at least one target client requires mso-font-alt.
        """
        needs_mso = any(
            self._clients.get(c, {}).get("requires_mso_font_alt", False) for c in target_clients
        )
        if not needs_mso:
            return html

        def _inject(m: re.Match[str]) -> str:
            style = m.group(1)
            if "mso-font-alt" in style:
                return m.group(0)
            font_match = _FONT_FAMILY_RE.search(style)
            if not font_match:
                return m.group(0)
            alt = self.get_mso_font_alt(font_match.group(1))
            if not alt:
                return m.group(0)
            new_style = f"{style.rstrip(';')}; mso-font-alt: {alt}"
            quote = m.group(0)[m.group(0).index("=") + 1]  # " or '
            return f"style={quote}{new_style}{quote}"

        return _INLINE_STYLE_RE.sub(_inject, html)

    def _client_needs_fallback(self, client: str, font: str) -> bool:
        """Check if a client needs system font fallback."""
        info = self._clients.get(client)
        if not info:
            return False
        client_type = info.get("type", "all")
        if client_type == "all":
            return False
        if client_type == "system":
            supported = {f.lower() for f in info.get("fonts", [])}
            return font.lower() not in supported
        return False

    @staticmethod
    def _parse_stack(font_family: str) -> list[str]:
        """Parse a font-family value into individual font names."""
        return [f.strip() for f in font_family.split(",") if f.strip()]
