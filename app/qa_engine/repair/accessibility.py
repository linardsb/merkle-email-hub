"""Stage 4: Accessibility structural fixes — lang, role, scope, alt."""

from __future__ import annotations

import re

from app.qa_engine.repair.pipeline import RepairResult

_HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
_LANG_ATTR_RE = re.compile(r"\blang\s*=", re.IGNORECASE)

# Layout table: <table> without data-content attribute
_TABLE_RE = re.compile(r"<table\b([^>]*)>", re.IGNORECASE)
_ROLE_ATTR_RE = re.compile(r"\brole\s*=", re.IGNORECASE)
_DATA_CONTENT_RE = re.compile(r"\bdata-content\b", re.IGNORECASE)

_TH_RE = re.compile(r"<th\b([^>]*)>", re.IGNORECASE)
_SCOPE_ATTR_RE = re.compile(r"\bscope\s*=", re.IGNORECASE)

_IMG_RE = re.compile(r"<img\b([^>]*?)(/?>)", re.IGNORECASE)
_ALT_ATTR_RE = re.compile(r"\balt\s*=", re.IGNORECASE)


class AccessibilityRepair:
    """Add missing accessibility attributes (lang, role, scope, alt)."""

    @property
    def name(self) -> str:
        return "accessibility"

    def repair(self, html: str) -> RepairResult:
        repairs: list[str] = []
        warnings: list[str] = []
        result = html

        # 1. Add lang="en" to <html> if missing
        html_match = _HTML_TAG_RE.search(result)
        if html_match and not _LANG_ATTR_RE.search(html_match.group(1)):
            attrs = html_match.group(1)
            new_tag = f'<html{attrs} lang="en">'
            result = result[: html_match.start()] + new_tag + result[html_match.end() :]
            repairs.append("added_lang")

        # 2. Add role="presentation" to layout tables (those without data-content)
        table_count = 0

        def _add_role(m: re.Match[str]) -> str:
            nonlocal table_count
            attrs = m.group(1)
            if _ROLE_ATTR_RE.search(attrs) or _DATA_CONTENT_RE.search(attrs):
                return m.group(0)
            table_count += 1
            return f'<table{attrs} role="presentation">'

        result = _TABLE_RE.sub(_add_role, result)
        if table_count:
            repairs.append(f"added_role_presentation_{table_count}")

        # 3. Add scope="col" to <th> elements missing scope
        th_count = 0

        def _add_scope(m: re.Match[str]) -> str:
            nonlocal th_count
            attrs = m.group(1)
            if _SCOPE_ATTR_RE.search(attrs):
                return m.group(0)
            th_count += 1
            return f'<th{attrs} scope="col">'

        result = _TH_RE.sub(_add_scope, result)
        if th_count:
            repairs.append(f"added_scope_{th_count}")

        # 4. Add alt="" to images missing alt attribute
        img_count = 0

        def _add_alt(m: re.Match[str]) -> str:
            nonlocal img_count
            attrs = m.group(1)
            closing = m.group(2)
            if _ALT_ATTR_RE.search(attrs):
                return m.group(0)
            img_count += 1
            return f'<img{attrs} alt=""{closing}'

        result = _IMG_RE.sub(_add_alt, result)
        if img_count:
            repairs.append(f"added_empty_alt_{img_count}")
            warnings.append(
                f'accessibility.empty_alt: {img_count} image(s) given alt="" — '
                "review for meaningful alt text"
            )

        return RepairResult(html=result, repairs_applied=repairs, warnings=warnings)
