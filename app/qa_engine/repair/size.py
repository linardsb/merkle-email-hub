"""Stage 6: Size optimisation — strip comments, clean empty attrs."""

from __future__ import annotations

import re

from app.qa_engine.repair.pipeline import RepairResult

# HTML comments EXCEPT MSO conditionals (<!--[if and <![endif]-->)
_NON_MSO_COMMENT_RE = re.compile(
    r"<!--(?!\[if\s)(?!\[endif)(?!<!\[endif).*?-->",
    re.DOTALL,
)

# Empty style attributes
_EMPTY_STYLE_RE = re.compile(r'\s+style\s*=\s*""\s*', re.IGNORECASE)
_EMPTY_STYLE_SPACE_RE = re.compile(r'\s+style\s*=\s*"\s+"\s*', re.IGNORECASE)


class SizeRepair:
    """Reduce HTML payload: strip comments and clean empty style attrs."""

    @property
    def name(self) -> str:
        return "size"

    def repair(self, html: str) -> RepairResult:
        repairs: list[str] = []
        result = html

        # 1. Strip HTML comments except MSO conditionals
        stripped = _NON_MSO_COMMENT_RE.sub("", result)
        if stripped != result:
            repairs.append("stripped_comments")
            result = stripped

        # 2. Remove empty style="" attributes
        cleaned = _EMPTY_STYLE_RE.sub(" ", result)
        cleaned = _EMPTY_STYLE_SPACE_RE.sub(" ", cleaned)
        if cleaned != result:
            repairs.append("removed_empty_styles")
            result = cleaned

        return RepairResult(html=result, repairs_applied=repairs)
