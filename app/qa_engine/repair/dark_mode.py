"""Stage 3: Dark mode meta tag injection — wraps existing meta_injector."""

from __future__ import annotations

import re

from app.qa_engine.repair.pipeline import RepairResult

# Pattern to find existing prefers-color-scheme media query
_DARK_MODE_MQ_RE = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", re.IGNORECASE)
_STYLE_CLOSE_RE = re.compile(r"</style\s*>", re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)


class DarkModeRepair:
    """Inject missing dark mode meta tags and media query placeholder."""

    @property
    def name(self) -> str:
        return "dark_mode"

    def repair(self, html: str) -> RepairResult:
        from app.ai.agents.dark_mode.meta_injector import inject_missing_meta_tags

        repairs: list[str] = []

        # Step 1: Inject missing meta tags using existing utility
        meta_result = inject_missing_meta_tags(html)
        result = meta_result.html
        if meta_result.injected_tags:
            repairs.extend(f"meta_{tag}" for tag in meta_result.injected_tags)

        # Step 2: Ensure @media (prefers-color-scheme: dark) exists
        if not _DARK_MODE_MQ_RE.search(result):
            dark_mode_css = (
                "\n@media (prefers-color-scheme: dark) {\n  /* dark mode overrides */\n}\n"
            )

            # Try to inject before last </style>
            style_matches = list(_STYLE_CLOSE_RE.finditer(result))
            if style_matches:
                last_style = style_matches[-1]
                result = result[: last_style.start()] + dark_mode_css + result[last_style.start() :]
                repairs.append("media_query_placeholder")
            else:
                # No <style> tag — create one in <head>
                head_match = _HEAD_CLOSE_RE.search(result)
                if head_match:
                    style_block = f"\n<style>{dark_mode_css}</style>\n"
                    result = (
                        result[: head_match.start()] + style_block + result[head_match.start() :]
                    )
                    repairs.append("style_block_with_media_query")

        return RepairResult(html=result, repairs_applied=repairs)
