"""Stage 7: Link validation & fix — empty hrefs, javascript: warnings, URL checks."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.qa_engine.repair.pipeline import RepairResult

# Match href with double or single quotes via backreference
_HREF_RE = re.compile(r"href\s*=\s*([\"'])(.+?)\1", re.IGNORECASE)
_EMPTY_HREF_RE = re.compile(r"href\s*=\s*([\"'])\1", re.IGNORECASE)
_JAVASCRIPT_HREF_RE = re.compile(r"href\s*=\s*[\"']javascript:", re.IGNORECASE)

# Valid schemes for email links
_VALID_SCHEMES = {"http", "https", "mailto", "tel", ""}


class LinkRepair:
    """Fix empty hrefs and warn on suspicious link patterns."""

    @property
    def name(self) -> str:
        return "links"

    def repair(self, html: str) -> RepairResult:
        repairs: list[str] = []
        warnings: list[str] = []
        result = html

        # 1. Replace empty href="" / href='' with href="#"
        if _EMPTY_HREF_RE.search(result):
            result = _EMPTY_HREF_RE.sub('href="#"', result)
            repairs.append("fixed_empty_hrefs")

        # 2. Warn on javascript: hrefs (don't remove — might be intentional)
        js_matches = list(_JAVASCRIPT_HREF_RE.finditer(result))
        if js_matches:
            warnings.append(
                f"links.javascript_href: {len(js_matches)} link(s) use javascript: protocol"
            )

        # 3. Validate href schemes
        for match in _HREF_RE.finditer(result):
            href = match.group(2)
            # Skip template variables ({{ }}, %% %%, etc.)
            if "{{" in href or "%%" in href or "{%" in href:
                continue
            # Skip anchors and relative paths
            if href.startswith(("#", "/", "./", "../")):
                continue
            try:
                parsed = urlparse(href)
                if parsed.scheme and parsed.scheme not in _VALID_SCHEMES:
                    warnings.append(f"links.invalid_scheme: href='{href[:80]}'")
            except Exception:
                warnings.append(f"links.unparseable: href='{href[:80]}'")

        return RepairResult(html=result, repairs_applied=repairs, warnings=warnings)
