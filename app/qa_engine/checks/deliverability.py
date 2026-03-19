"""Deliverability prediction score — 4-dimension pre-send inbox placement analysis.

Scores email HTML across four dimensions (0-25 each) for a total 0-100 score:
- Content quality: text-to-image ratio, link density, URL shorteners, excessive caps
- HTML hygiene: DOCTYPE, encoding, size, hidden text, single-image emails
- Authentication readiness: List-Unsubscribe, unsubscribe link, sender patterns
- Engagement signals: preview text, personalization tokens, primary CTA, content length

Does NOT duplicate spam_score check (trigger phrases, formatting heuristics).
Pure CPU — no LLM, no DB, no external APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from lxml import html as lxml_html

from app.qa_engine.deliverability_analyzer import (
    DeliverabilityAnalysis,
    colors_within_brightness,
    parse_color,
)
from app.qa_engine.deliverability_analyzer import (
    analyze as isp_analyze,
)
from app.qa_engine.schemas import QACheckResult

if TYPE_CHECKING:
    from lxml.html import HtmlElement

    from app.qa_engine.check_config import QACheckConfig


@dataclass(frozen=True)
class _Issue:
    """Internal issue representation."""

    dimension: str
    severity: str  # error | warning | info
    description: str
    fix: str
    penalty: int  # points deducted from dimension's 25


@dataclass
class _DimensionResult:
    """Internal dimension scoring result."""

    name: str
    max_score: int = 25
    issues: list[_Issue] = field(default_factory=lambda: [])

    @property
    def score(self) -> int:
        total_penalty = sum(i.penalty for i in self.issues)
        return max(0, self.max_score - total_penalty)


# --- URL shortener domains (static, no dynamic loading) ---
_URL_SHORTENERS: frozenset[str] = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "short.to",
        "rebrand.ly",
    }
)

_CAPS_WORD_RE = re.compile(r"\b[A-Z]{4,}\b")  # 4+ consecutive caps

_GMAIL_CLIP_SIZE = 102 * 1024  # 102KB

_UNSUB_LINK_RE = re.compile(r"unsubscribe|opt[\s-]?out|manage[\s-]?preferences", re.IGNORECASE)
_LIST_UNSUB_RE = re.compile(r"list-unsubscribe", re.IGNORECASE)

_ADDRESS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln)",
        re.IGNORECASE,
    ),
    re.compile(r"p\.?\s*o\.?\s*box\s+\d+", re.IGNORECASE),
    re.compile(r"suite\s+\d+", re.IGNORECASE),
)

_PREVIEW_TEXT_RE = re.compile(
    r'class\s*=\s*["\'][^"\']*preview[^"\']*["\']',
    re.IGNORECASE,
)
_PERSONALIZATION_RE = re.compile(
    r"\{\{[^}]+\}\}|<%[^%]+%>|\$\{[^}]+\}|\*\|[^|]+\|\*|%%[^%]+%%",
)
_CTA_RE = re.compile(
    r"(shop\s+now|buy\s+now|learn\s+more|get\s+started|sign\s+up|register|download"
    r"|try\s+free|order\s+now|subscribe|read\s+more|view\s+details|claim|explore"
    r"|discover|start|join)",
    re.IGNORECASE,
)

# Common abbreviations to exclude from ALL-CAPS detection
_CAPS_ALLOWLIST: frozenset[str] = frozenset(
    {
        "HTML",
        "CSS",
        "HTTP",
        "HTTPS",
        "URL",
        "CTA",
        "ESP",
        "DKIM",
        "SPF",
        "DMARC",
        "BIMI",
        "MIME",
    }
)


def _score_content_quality(doc: HtmlElement, _html: str) -> _DimensionResult:
    """Score content quality: text-to-image ratio, link density, shorteners, caps."""
    result = _DimensionResult(name="content_quality")

    # Extract visible text
    text_content = doc.text_content() or ""
    text_length = len(text_content.strip())
    images = doc.xpath("//img")
    image_count = len(images)

    # Text-to-image ratio: penalize if images dominate
    total_elements = text_length + (image_count * 1000)  # estimate 1000 chars per image
    if total_elements > 0:
        text_ratio = text_length / total_elements
        if text_ratio < 0.3:
            result.issues.append(
                _Issue(
                    dimension="content_quality",
                    severity="error",
                    description=f"Very low text-to-image ratio ({text_ratio:.0%}). Email appears image-heavy.",
                    fix="Add more text content. Aim for at least 60% text to 40% images.",
                    penalty=10,
                )
            )
        elif text_ratio < 0.6:
            result.issues.append(
                _Issue(
                    dimension="content_quality",
                    severity="warning",
                    description=f"Low text-to-image ratio ({text_ratio:.0%}).",
                    fix="Add more text content to improve deliverability.",
                    penalty=5,
                )
            )

    # Link density: < 1 link per 50 words is good
    links = doc.xpath("//a[@href]")
    word_count = len(text_content.split())
    if word_count > 0 and len(links) > 0:
        words_per_link = word_count / len(links)
        if words_per_link < 25:
            result.issues.append(
                _Issue(
                    dimension="content_quality",
                    severity="warning",
                    description=(
                        f"High link density ({len(links)} links for {word_count} words, "
                        f"{words_per_link:.0f} words/link)."
                    ),
                    fix="Reduce number of links. Aim for fewer than 1 link per 50 words.",
                    penalty=5,
                )
            )
        elif words_per_link < 50:
            result.issues.append(
                _Issue(
                    dimension="content_quality",
                    severity="info",
                    description=f"Moderate link density ({words_per_link:.0f} words per link).",
                    fix="Consider reducing links for better deliverability.",
                    penalty=2,
                )
            )

    # URL shorteners
    for link in links:
        href = (link.get("href") or "").lower()
        for shortener in _URL_SHORTENERS:
            if shortener in href:
                result.issues.append(
                    _Issue(
                        dimension="content_quality",
                        severity="error",
                        description=f"URL shortener detected: {shortener}. Spam filters flag shortened URLs.",
                        fix="Replace shortened URLs with full destination URLs.",
                        penalty=8,
                    )
                )
                break  # one penalty per shortener domain found

    # Excessive capitalization in visible text (not in HTML tags)
    caps_matches = _CAPS_WORD_RE.findall(text_content)
    caps_words = [w for w in caps_matches if w not in _CAPS_ALLOWLIST]
    if len(caps_words) > 5:
        result.issues.append(
            _Issue(
                dimension="content_quality",
                severity="warning",
                description=f"Excessive capitalization: {len(caps_words)} ALL-CAPS words detected.",
                fix="Reduce use of ALL-CAPS words. Use proper casing instead.",
                penalty=5,
            )
        )

    return result


def _score_html_hygiene(doc: HtmlElement, html: str) -> _DimensionResult:
    """Score HTML hygiene: DOCTYPE, encoding, size, hidden text, single-image."""
    result = _DimensionResult(name="html_hygiene")

    html_lower = html.lower()

    # DOCTYPE present
    if "<!doctype" not in html_lower:
        result.issues.append(
            _Issue(
                dimension="html_hygiene",
                severity="error",
                description="Missing DOCTYPE declaration.",
                fix="Add <!DOCTYPE html> at the beginning of the email.",
                penalty=5,
            )
        )

    # Character encoding declared
    has_charset_meta = bool(re.search(r"<meta[^>]+charset\s*=", html_lower))
    has_content_type = bool(re.search(r"<meta[^>]+content-type[^>]+charset", html_lower))
    if not has_charset_meta and not has_content_type:
        result.issues.append(
            _Issue(
                dimension="html_hygiene",
                severity="warning",
                description="No character encoding declared.",
                fix='Add <meta charset="utf-8"> in the <head>.',
                penalty=3,
            )
        )

    # HTML size check (Gmail clips at 102KB)
    html_bytes = len(html.encode("utf-8"))
    if html_bytes > _GMAIL_CLIP_SIZE:
        result.issues.append(
            _Issue(
                dimension="html_hygiene",
                severity="error",
                description=f"HTML size ({html_bytes:,} bytes) exceeds Gmail's 102KB clipping threshold.",
                fix="Reduce HTML size below 102KB to prevent clipping.",
                penalty=8,
            )
        )
    elif html_bytes > int(_GMAIL_CLIP_SIZE * 0.85):
        result.issues.append(
            _Issue(
                dimension="html_hygiene",
                severity="warning",
                description=f"HTML size ({html_bytes:,} bytes) is close to Gmail's 102KB clipping threshold.",
                fix="Consider reducing HTML size for safety margin.",
                penalty=3,
            )
        )

    # Hidden text detection (text color matching background)
    _check_hidden_text(doc, result)

    # Single-image email (body is just one <img>)
    body = doc.xpath("//body")
    if body:
        body_text = (body[0].text_content() or "").strip()
        body_images = body[0].xpath(".//img")
        if len(body_images) >= 1 and len(body_text) < 50:
            result.issues.append(
                _Issue(
                    dimension="html_hygiene",
                    severity="error",
                    description="Single-image email detected. Minimal text content with images.",
                    fix="Add substantial text content alongside images. Single-image emails are flagged by spam filters.",
                    penalty=10,
                )
            )

    return result


def _check_hidden_text(doc: HtmlElement, result: _DimensionResult) -> None:
    """Detect hidden text — brightness proximity, font-size:0, visibility:hidden."""
    for el in doc.xpath("//*[@style]"):
        style = (el.get("style") or "").lower()
        tag = el.tag
        el_class = (el.get("class") or "").lower()
        is_preheader = "preheader" in el_class or "preview" in el_class

        # Color/background brightness proximity (enhanced from exact match)
        color_match = re.search(r"(?:^|;)\s*color\s*:\s*([^;!]+)", style)
        bg_match = re.search(r"background(?:-color)?\s*:\s*([^;!]+)", style)
        if color_match and bg_match:
            fg = parse_color(color_match.group(1))
            bg = parse_color(bg_match.group(1))
            if fg and bg and colors_within_brightness(fg, bg, 10):
                result.issues.append(
                    _Issue(
                        dimension="html_hygiene",
                        severity="error",
                        description=(
                            f"Hidden text detected: <{tag}> text color and background "
                            "within 10% brightness."
                        ),
                        fix="Ensure text color contrasts visibly with background color.",
                        penalty=10,
                    )
                )
                return

        # font-size: 0 (not preheader)
        font_match = re.search(r"font-size\s*:\s*0(?:px|em|rem|%)?\s*(?:;|$)", style)
        if font_match and not is_preheader:
            result.issues.append(
                _Issue(
                    dimension="html_hygiene",
                    severity="error",
                    description=f"Hidden text: <{tag}> has font-size: 0.",
                    fix="Remove zero-size text or use a visible font size.",
                    penalty=10,
                )
            )
            return

        # visibility:hidden on content
        if "visibility" in style and "hidden" in style:
            text = (el.text_content() or "").strip()
            if len(text) > 10 and not is_preheader:
                result.issues.append(
                    _Issue(
                        dimension="html_hygiene",
                        severity="error",
                        description=f"Hidden text: <{tag}> with visibility:hidden ({len(text)} chars).",
                        fix="Remove hidden content or make it visible.",
                        penalty=10,
                    )
                )
                return


def _score_auth_readiness(doc: HtmlElement, html: str) -> _DimensionResult:
    """Score authentication readiness: List-Unsubscribe, unsub link, sender patterns."""
    result = _DimensionResult(name="auth_readiness")

    # List-Unsubscribe header hint (checked in HTML comments or meta tags)
    has_list_unsub_meta = bool(_LIST_UNSUB_RE.search(html))
    if not has_list_unsub_meta:
        result.issues.append(
            _Issue(
                dimension="auth_readiness",
                severity="warning",
                description="No List-Unsubscribe header hint found.",
                fix="Add List-Unsubscribe header when sending. Include as a meta tag or comment for template awareness.",
                penalty=8,
            )
        )

    # Unsubscribe link in body
    links = doc.xpath("//a[@href]")
    has_unsub_link = False
    for link in links:
        href = link.get("href") or ""
        text = (link.text_content() or "").strip()
        if _UNSUB_LINK_RE.search(href) or _UNSUB_LINK_RE.search(text):
            has_unsub_link = True
            break
    if not has_unsub_link:
        result.issues.append(
            _Issue(
                dimension="auth_readiness",
                severity="error",
                description="No unsubscribe link found in email body.",
                fix='Add a visible unsubscribe link (e.g., <a href="{{unsubscribe_url}}">Unsubscribe</a>).',
                penalty=12,
            )
        )

    # Physical address presence (CAN-SPAM requirement)
    text_content = (doc.text_content() or "").lower()
    has_address = any(p.search(text_content) for p in _ADDRESS_PATTERNS)
    if not has_address:
        result.issues.append(
            _Issue(
                dimension="auth_readiness",
                severity="info",
                description="No physical mailing address detected (CAN-SPAM requirement).",
                fix="Include your physical mailing address in the email footer.",
                penalty=5,
            )
        )

    return result


def _score_engagement_signals(doc: HtmlElement, html: str) -> _DimensionResult:
    """Score engagement signals: preview text, personalization, CTA, content length."""
    result = _DimensionResult(name="engagement_signals")

    # Preview text present (hidden preheader text)
    has_preview = bool(_PREVIEW_TEXT_RE.search(html))
    # Also check for preheader-style hidden div patterns
    if not has_preview:
        for el in doc.xpath("//*[@style]"):
            style = (el.get("style") or "").lower()
            if "display:none" in style.replace(" ", "") or "max-height:0" in style.replace(" ", ""):
                text = (el.text_content() or "").strip()
                if len(text) > 10:
                    has_preview = True
                    break
    if not has_preview:
        result.issues.append(
            _Issue(
                dimension="engagement_signals",
                severity="warning",
                description="No preview text (preheader) detected.",
                fix="Add hidden preview text at the top of the email body for inbox previews.",
                penalty=6,
            )
        )

    # Personalization tokens
    personalization_matches = _PERSONALIZATION_RE.findall(html)
    if not personalization_matches:
        result.issues.append(
            _Issue(
                dimension="engagement_signals",
                severity="info",
                description="No personalization tokens detected.",
                fix="Add personalization (e.g., {{first_name}}) to improve engagement.",
                penalty=4,
            )
        )

    # Clear primary CTA
    links = doc.xpath("//a")
    has_cta = False
    for link in links:
        text = (link.text_content() or "").strip()
        if _CTA_RE.search(text):
            has_cta = True
            break
        # Also check for CTA-style buttons (links with background-color in style)
        style = (link.get("style") or "").lower()
        if "background" in style and text and len(text) < 30:
            has_cta = True
            break
    if not has_cta:
        result.issues.append(
            _Issue(
                dimension="engagement_signals",
                severity="warning",
                description="No clear call-to-action (CTA) detected.",
                fix="Add a prominent CTA button with action-oriented text (e.g., 'Shop Now', 'Learn More').",
                penalty=6,
            )
        )

    # Content length check
    html_text = doc.text_content() or ""
    word_count = len(html_text.split())
    if word_count < 20:
        result.issues.append(
            _Issue(
                dimension="engagement_signals",
                severity="warning",
                description=f"Very short content ({word_count} words).",
                fix="Add more content. Very short emails may appear spammy.",
                penalty=6,
            )
        )
    elif word_count > 2000:
        result.issues.append(
            _Issue(
                dimension="engagement_signals",
                severity="info",
                description=f"Long content ({word_count} words). May reduce engagement.",
                fix="Consider shortening content for better engagement rates.",
                penalty=3,
            )
        )

    return result


class DeliverabilityCheck:
    """Pre-send deliverability prediction scoring (check #13).

    Scores email HTML across 4 dimensions (0-25 each) for a 0-100 total.
    Pass threshold configurable via QA__DELIVERABILITY_THRESHOLD (default 70).
    """

    name: str = "deliverability"

    async def run(self, html: str, config: QACheckConfig | None = None) -> QACheckResult:
        """Run deliverability scoring across all 4 dimensions + ISP-specific analysis."""
        try:
            doc = lxml_html.fromstring(html)
        except Exception:
            return QACheckResult(
                check_name=self.name,
                passed=False,
                score=0.0,
                details="Failed to parse HTML for deliverability analysis.",
                severity="error",
            )

        # Score each dimension
        dimensions = [
            _score_content_quality(doc, html),
            _score_html_hygiene(doc, html),
            _score_auth_readiness(doc, html),
            _score_engagement_signals(doc, html),
        ]

        total_score = sum(d.score for d in dimensions)
        threshold = 70
        if config and config.params.get("threshold"):
            threshold = int(config.params["threshold"])

        # --- ISP-specific analysis ---
        isp_analysis = isp_analyze(html)
        isp_penalty = min(15, isp_analysis.total_isp_flags * 2)
        total_score = max(0, total_score - isp_penalty)

        passed = total_score >= threshold

        # Build details string
        dimension_lines = [f"{d.name}: {d.score}/{d.max_score}" for d in dimensions]
        issue_lines: list[str] = []
        for d in dimensions:
            for issue in d.issues:
                issue_lines.append(f"[{issue.severity}] {issue.description} → {issue.fix}")

        # Add ISP-specific flags
        for _isp_name, profile in isp_analysis.isp_risks.items():
            for flag in profile.flags:
                issue_lines.append(
                    f"[{flag.severity}] [{flag.isp.upper()}] {flag.description} → {flag.fix}"
                )

        # Add structural flags from ISP analysis
        for sf in isp_analysis.structural_flags:
            if sf not in issue_lines:
                issue_lines.append(sf)

        details = f"Score: {total_score}/100 (threshold: {threshold})"
        details += f" | ISP penalty: -{isp_penalty}"
        details += f" | Overall risk: {isp_analysis.overall_risk}\n"
        details += " | ".join(dimension_lines)

        # Per-ISP summary
        for _isp_name, profile in isp_analysis.isp_risks.items():
            details += (
                f"\n{profile.display_name}: risk={profile.risk_level}, score={profile.score}/100"
            )

        if issue_lines:
            details += "\n" + "\n".join(issue_lines)

        # Severity based on score and ISP risk
        if total_score < 40 or isp_analysis.overall_risk == "critical":
            severity = "error"
        elif total_score < threshold or isp_analysis.overall_risk == "high":
            severity = "warning"
        else:
            severity = "info"

        return QACheckResult(
            check_name=self.name,
            passed=passed,
            score=total_score / 100.0,
            details=details,
            severity=severity,
        )


def get_detailed_result(
    html: str,
    threshold: int = 70,
) -> tuple[int, bool, list[_DimensionResult], DeliverabilityAnalysis | None]:
    """Return (score, passed, dimensions, isp_analysis) for the standalone endpoint."""
    try:
        doc = lxml_html.fromstring(html)
    except Exception:
        return (0, False, [], None)

    dimensions = [
        _score_content_quality(doc, html),
        _score_html_hygiene(doc, html),
        _score_auth_readiness(doc, html),
        _score_engagement_signals(doc, html),
    ]
    total = sum(d.score for d in dimensions)

    analysis = isp_analyze(html)
    isp_penalty = min(15, analysis.total_isp_flags * 2)
    total = max(0, total - isp_penalty)

    return (total, total >= threshold, dimensions, analysis)
