"""ISP-aware deliverability analyzer with structured output.

Loads ISP profiles from data/isp_profiles.yaml and provides ISP-specific
risk analysis on top of the base deliverability check dimensions.
Pure CPU — no LLM, no DB, no external APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.core.logging import get_logger

logger = get_logger(__name__)

_PROFILES_PATH = Path(__file__).parent / "data" / "isp_profiles.yaml"


@dataclass(frozen=True)
class ISPFlag:
    """A single ISP-specific deliverability flag."""

    isp: str
    category: str  # promo_tab | smartscreen | sender_reputation | structural
    severity: str  # error | warning | info
    description: str
    threshold: str  # the threshold that was violated
    fix: str  # concrete remediation


@dataclass(frozen=True)
class HiddenTextFlag:
    """A hidden text detection result."""

    element_tag: str
    technique: str  # color_match | font_size | display_none | visibility | opacity
    description: str
    fix: str


@dataclass
class ISPRiskProfile:
    """Risk assessment for a single ISP."""

    isp: str
    display_name: str
    risk_level: str = "low"  # low | medium | high | critical
    flags: list[ISPFlag] = field(default_factory=list)
    score: int = 100  # 0-100, deducted per flag


@dataclass
class DeliverabilityAnalysis:
    """Complete ISP-aware deliverability analysis."""

    image_text_ratio: float
    link_density: float  # links per 100 words
    hidden_content_count: int
    auth_readiness_score: int  # 0-25
    isp_risks: dict[str, ISPRiskProfile] = field(default_factory=dict)
    structural_flags: list[str] = field(default_factory=list)
    overall_risk: str = "low"  # low | medium | high | critical
    gmail_promo_tab_score: int = 0  # 0 = unlikely promo, higher = more likely

    @property
    def total_isp_flags(self) -> int:
        return sum(len(p.flags) for p in self.isp_risks.values())


@lru_cache(maxsize=1)
def _load_isp_profiles() -> dict[str, Any]:
    """Load and cache ISP profiles from YAML."""
    if not _PROFILES_PATH.exists():
        logger.warning("isp_profiles.yaml not found, using empty profiles")
        return {}
    with _PROFILES_PATH.open() as f:
        return yaml.safe_load(f) or {}


def _parse_hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
    """Parse #RGB or #RRGGBB to (r, g, b) tuple."""
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return None
    try:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    except ValueError:
        return None


_CSS_COLOR_NAMES: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "transparent": (0, 0, 0),  # treated as black for comparison
}


def parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse a CSS color value to RGB tuple."""
    color_str = color_str.strip().lower()
    if color_str in _CSS_COLOR_NAMES:
        return _CSS_COLOR_NAMES[color_str]
    if color_str.startswith("#"):
        return _parse_hex_to_rgb(color_str)
    rgb_match = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color_str)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))
    return None


def brightness(r: int, g: int, b: int) -> float:
    """Perceived brightness (0.0-1.0) using HSP model."""
    return float((0.299 * r * r + 0.587 * g * g + 0.114 * b * b) ** 0.5 / 255.0)


def colors_within_brightness(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
    threshold_pct: float,
) -> bool:
    """Check if two colors are within brightness threshold percentage."""
    b1 = brightness(*c1)
    b2 = brightness(*c2)
    return abs(b1 - b2) < (threshold_pct / 100.0)


def _detect_hidden_text(
    doc: HtmlElement,
    profiles: dict[str, Any],
) -> list[HiddenTextFlag]:
    """Enhanced hidden text detection with brightness proximity."""
    flags: list[HiddenTextFlag] = []
    hidden_config = profiles.get("hidden_text", {})
    brightness_pct = hidden_config.get("brightness_proximity_pct", 10)
    min_font_px = hidden_config.get("min_font_size_px", 1)

    for el in doc.xpath("//*[@style]"):
        style = (el.get("style") or "").lower()
        tag = el.tag

        # 1. Color/background brightness proximity
        color_match = re.search(r"(?:^|;)\s*color\s*:\s*([^;!]+)", style)
        bg_match = re.search(r"background(?:-color)?\s*:\s*([^;!]+)", style)
        if color_match and bg_match:
            fg = parse_color(color_match.group(1))
            bg = parse_color(bg_match.group(1))
            if fg and bg and colors_within_brightness(fg, bg, brightness_pct):
                flags.append(
                    HiddenTextFlag(
                        element_tag=tag,
                        technique="color_match",
                        description=(
                            f"<{tag}> has text color and background within "
                            f"{brightness_pct}% brightness — appears hidden."
                        ),
                        fix="Ensure text color contrasts with background color.",
                    )
                )

        # 2. Font-size: 0 or tiny
        font_match = re.search(r"font-size\s*:\s*(\d+)", style)
        if font_match and int(font_match.group(1)) < min_font_px:
            # Check if this is a known preheader pattern
            el_class = (el.get("class") or "").lower()
            if "preheader" not in el_class and "preview" not in el_class:
                flags.append(
                    HiddenTextFlag(
                        element_tag=tag,
                        technique="font_size",
                        description=f"<{tag}> has font-size: {font_match.group(1)}px — hidden text.",
                        fix="Remove zero-size text or use visible font size.",
                    )
                )

        # 3. display:none on content elements (exclude preheader/preview)
        if "display" in style and "none" in style:
            normalized = style.replace(" ", "")
            if "display:none" in normalized:
                el_class = (el.get("class") or "").lower()
                text = (el.text_content() or "").strip()
                is_preheader = "preheader" in el_class or "preview" in el_class
                if not is_preheader and len(text) > 20:
                    flags.append(
                        HiddenTextFlag(
                            element_tag=tag,
                            technique="display_none",
                            description=f"<{tag}> with display:none contains substantial text ({len(text)} chars).",
                            fix="Remove hidden content or make it visible.",
                        )
                    )

        # 4. visibility:hidden
        if "visibility" in style and "hidden" in style:
            text = (el.text_content() or "").strip()
            if len(text) > 10:
                flags.append(
                    HiddenTextFlag(
                        element_tag=tag,
                        technique="visibility",
                        description=f"<{tag}> with visibility:hidden contains text ({len(text)} chars).",
                        fix="Remove hidden content or make it visible.",
                    )
                )

        # 5. opacity:0
        opacity_match = re.search(r"opacity\s*:\s*0(?:\.0+)?(?:;|$)", style)
        if opacity_match:
            text = (el.text_content() or "").strip()
            el_class = (el.get("class") or "").lower()
            if len(text) > 10 and "preheader" not in el_class:
                flags.append(
                    HiddenTextFlag(
                        element_tag=tag,
                        technique="opacity",
                        description=f"<{tag}> with opacity:0 contains text ({len(text)} chars).",
                        fix="Remove transparent content or make it visible.",
                    )
                )

    return flags


def _analyze_gmail_promo_tab(
    doc: HtmlElement,
    gmail_config: dict[str, Any],
) -> tuple[int, list[ISPFlag]]:
    """Score Gmail Promotions tab likelihood. Higher = more likely promo."""
    flags: list[ISPFlag] = []
    total_weight = 0
    text_content = doc.text_content() or ""

    for trigger in gmail_config.get("promo_tab_triggers", []):
        pattern = trigger.get("pattern", "")
        weight = trigger.get("weight", 1)
        description = trigger.get("description", pattern)
        if re.search(pattern, text_content, re.IGNORECASE):
            total_weight += weight
            flags.append(
                ISPFlag(
                    isp="gmail",
                    category="promo_tab",
                    severity="warning" if weight >= 3 else "info",
                    description=f"Gmail Promotions tab trigger: {description}.",
                    threshold=f"Pattern weight: {weight}",
                    fix=f"Reduce promotional language: {description.lower()}.",
                )
            )

    return total_weight, flags


def _analyze_microsoft_smartscreen(
    doc: HtmlElement,
    ms_config: dict[str, Any],
) -> list[ISPFlag]:
    """Analyze Microsoft SmartScreen risk patterns."""
    flags: list[ISPFlag] = []
    text_content = doc.text_content() or ""
    thresholds = ms_config.get("thresholds", {})

    # Total link count
    links = doc.xpath("//a[@href]")
    link_max = thresholds.get("smartscreen_link_max", 15)
    if len(links) > link_max:
        flags.append(
            ISPFlag(
                isp="microsoft",
                category="smartscreen",
                severity="warning",
                description=f"Link count ({len(links)}) exceeds Microsoft SmartScreen threshold ({link_max}).",
                threshold=f"smartscreen_link_max: {link_max}",
                fix=f"Reduce total links to {link_max} or fewer.",
            )
        )

    # SmartScreen patterns
    for pattern_def in ms_config.get("smartscreen_patterns", []):
        pattern = pattern_def.get("pattern", "")
        weight = pattern_def.get("weight", 1)
        description = pattern_def.get("description", pattern)
        if re.search(pattern, text_content, re.IGNORECASE):
            severity = "error" if weight >= 3 else "warning"
            flags.append(
                ISPFlag(
                    isp="microsoft",
                    category="smartscreen",
                    severity=severity,
                    description=f"Microsoft SmartScreen pattern: {description}.",
                    threshold=f"Pattern weight: {weight}",
                    fix=f"Rephrase to avoid SmartScreen trigger: {description.lower()}.",
                )
            )

    return flags


def _analyze_yahoo_reputation(
    doc: HtmlElement,
    yahoo_config: dict[str, Any],
) -> list[ISPFlag]:
    """Analyze Yahoo/AOL sender reputation signals in HTML."""
    flags: list[ISPFlag] = []

    # Footer presence
    footer_els = doc.xpath(
        "//footer | //*[contains(@class, 'footer')] | //*[contains(@id, 'footer')]"
    )
    if not footer_els:
        flags.append(
            ISPFlag(
                isp="yahoo",
                category="sender_reputation",
                severity="warning",
                description="No footer element detected (Yahoo/AOL sender reputation signal).",
                threshold="footer_required: true",
                fix="Add a <footer> or element with class='footer' containing company info.",
            )
        )

    # Physical address (CAN-SPAM, but Yahoo weighs it heavily)
    text_content = doc.text_content() or ""
    address_patterns = (
        re.compile(
            r"\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln)",
            re.IGNORECASE,
        ),
        re.compile(r"p\.?\s*o\.?\s*box\s+\d+", re.IGNORECASE),
    )
    has_address = any(p.search(text_content) for p in address_patterns)
    if not has_address:
        flags.append(
            ISPFlag(
                isp="yahoo",
                category="sender_reputation",
                severity="warning",
                description="No physical mailing address detected (Yahoo/AOL reputation signal).",
                threshold="physical_address_required: true",
                fix="Add physical mailing address in the footer (CAN-SPAM requirement).",
            )
        )

    # Unsubscribe prominence — check it's not buried in tiny text
    unsub_re = re.compile(r"unsubscribe|opt[\s-]?out", re.IGNORECASE)
    for link in doc.xpath("//a"):
        text = (link.text_content() or "").strip()
        href = link.get("href") or ""
        if unsub_re.search(text) or unsub_re.search(href):
            style = (link.get("style") or "").lower()
            font_match = re.search(r"font-size\s*:\s*(\d+)", style)
            if font_match:
                size = int(font_match.group(1))
                min_size = (
                    yahoo_config.get("sender_reputation_signals", {})
                    .get("unsubscribe_prominence", {})
                    .get("min_font_size", 10)
                )
                if size < min_size:
                    flags.append(
                        ISPFlag(
                            isp="yahoo",
                            category="sender_reputation",
                            severity="info",
                            description=(
                                f"Unsubscribe link font-size ({size}px) below "
                                f"recommended minimum ({min_size}px)."
                            ),
                            threshold=f"min_font_size: {min_size}px",
                            fix=f"Increase unsubscribe link font-size to at least {min_size}px.",
                        )
                    )
            break  # only check first unsub link

    return flags


def _check_cross_domain_images(doc: HtmlElement) -> list[ISPFlag]:
    """Detect images from multiple different domains (SPF-breaking pattern)."""
    flags: list[ISPFlag] = []
    domains: set[str] = set()

    for img in doc.xpath("//img[@src]"):
        src = img.get("src") or ""
        domain_match = re.match(r"https?://([^/]+)", src)
        if domain_match:
            domains.add(domain_match.group(1).lower())

    if len(domains) > 3:
        flags.append(
            ISPFlag(
                isp="all",
                category="structural",
                severity="warning",
                description=(
                    f"Images loaded from {len(domains)} different domains. "
                    "Multiple external domains can affect authentication alignment."
                ),
                threshold="Recommended: ≤3 image domains",
                fix="Consolidate images to fewer domains, ideally your sending domain or CDN.",
            )
        )

    return flags


def _check_responsive_design(doc: HtmlElement, html: str) -> list[ISPFlag]:
    """Check for responsive design indicators."""
    flags: list[ISPFlag] = []

    has_media_query = bool(re.search(r"@media", html, re.IGNORECASE))

    # Check for wide tables without responsive support
    wide_tables = False
    for table in doc.xpath("//table[@width]"):
        width_str = table.get("width") or ""
        try:
            width = int(width_str.replace("px", "").strip())
            if width > 600:
                wide_tables = True
                break
        except ValueError:
            continue

    # Also check inline style widths
    if not wide_tables:
        for table in doc.xpath("//table[@style]"):
            style = table.get("style") or ""
            width_match = re.search(r"width\s*:\s*(\d+)\s*px", style)
            if width_match and int(width_match.group(1)) > 600:
                wide_tables = True
                break

    if wide_tables and not has_media_query:
        flags.append(
            ISPFlag(
                isp="all",
                category="structural",
                severity="warning",
                description=(
                    "Wide tables (>600px) detected without responsive media queries. "
                    "Mobile rendering issues trigger spam filters on some ISPs."
                ),
                threshold="Tables >600px require @media queries for mobile",
                fix="Add responsive @media queries or use max-width: 100% on tables.",
            )
        )

    return flags


def _check_tracking_params(doc: HtmlElement) -> list[ISPFlag]:
    """Detect excessive tracking parameters on links."""
    flags: list[ISPFlag] = []
    excessive_count = 0

    for link in doc.xpath("//a[@href]"):
        href = link.get("href") or ""
        if "?" not in href:
            continue
        query = href.split("?", 1)[1]
        params = query.count("&") + 1
        if params > 8:
            excessive_count += 1

    if excessive_count > 0:
        flags.append(
            ISPFlag(
                isp="all",
                category="structural",
                severity="info",
                description=f"{excessive_count} link(s) with excessive tracking parameters (>8 params).",
                threshold="Recommended: ≤8 URL parameters per link",
                fix="Consolidate tracking parameters. Excessive params look suspicious to filters.",
            )
        )

    return flags


def _score_to_risk(score: int) -> str:
    """Convert 0-100 score to risk level."""
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def analyze(html: str) -> DeliverabilityAnalysis:
    """Run full ISP-aware deliverability analysis.

    Returns a DeliverabilityAnalysis with per-ISP risk profiles and
    actionable remediation for every flag.
    """
    profiles = _load_isp_profiles()
    isps_config = profiles.get("isps", {})

    try:
        doc = lxml_html.fromstring(html)
    except Exception:
        return DeliverabilityAnalysis(
            image_text_ratio=0.0,
            link_density=0.0,
            hidden_content_count=0,
            auth_readiness_score=0,
            overall_risk="critical",
            structural_flags=["HTML could not be parsed"],
        )

    # --- Compute base metrics ---
    text_content = doc.text_content() or ""
    text_length = len(text_content.strip())
    images = doc.xpath("//img")
    image_count = len(images)
    total_elements = text_length + (image_count * 1000)
    image_text_ratio = (image_count * 1000) / total_elements if total_elements > 0 else 0.0

    word_count = len(text_content.split())
    links = doc.xpath("//a[@href]")
    link_density = (len(links) / (word_count / 100.0)) if word_count > 0 else 0.0

    # --- Hidden text ---
    hidden_flags = _detect_hidden_text(doc, profiles)

    # --- Per-ISP analysis ---
    isp_risks: dict[str, ISPRiskProfile] = {}
    promo_score = 0

    # Gmail
    gmail_cfg = isps_config.get("gmail", {})
    if gmail_cfg:
        gmail_profile = ISPRiskProfile(
            isp="gmail",
            display_name=gmail_cfg.get("display_name", "Gmail"),
        )
        gmail_thresholds = gmail_cfg.get("thresholds", {})

        # Image ratio vs Gmail threshold
        gmail_img_max = gmail_thresholds.get("image_text_ratio_max", 0.60)
        if image_text_ratio > gmail_img_max:
            gmail_profile.flags.append(
                ISPFlag(
                    isp="gmail",
                    category="structural",
                    severity="warning",
                    description=(
                        f"Image-to-text ratio is {image_text_ratio:.0%} "
                        f"(Gmail threshold: {gmail_img_max:.0%}). "
                        "Add more text content to body sections."
                    ),
                    threshold=f"image_text_ratio_max: {gmail_img_max:.0%}",
                    fix="Add 3+ lines of text to body section to improve ratio.",
                )
            )
            gmail_profile.score -= 15

        # Link density vs Gmail threshold
        gmail_link_max = gmail_thresholds.get("link_density_max", 3.0)
        if link_density > gmail_link_max:
            gmail_profile.flags.append(
                ISPFlag(
                    isp="gmail",
                    category="structural",
                    severity="warning",
                    description=(
                        f"Link density is {link_density:.1f} per 100 words "
                        f"(Gmail threshold: {gmail_link_max})."
                    ),
                    threshold=f"link_density_max: {gmail_link_max}",
                    fix="Reduce links or add more text content.",
                )
            )
            gmail_profile.score -= 10

        # Promotions tab analysis
        promo_score, promo_flags = _analyze_gmail_promo_tab(doc, gmail_cfg)
        gmail_profile.flags.extend(promo_flags)
        if promo_score >= 6:
            gmail_profile.score -= 20
        elif promo_score >= 3:
            gmail_profile.score -= 10

        gmail_profile.score = max(0, gmail_profile.score)
        gmail_profile.risk_level = _score_to_risk(gmail_profile.score)
        isp_risks["gmail"] = gmail_profile

    # Microsoft
    ms_cfg = isps_config.get("microsoft", {})
    if ms_cfg:
        ms_profile = ISPRiskProfile(
            isp="microsoft",
            display_name=ms_cfg.get("display_name", "Microsoft"),
        )
        ms_thresholds = ms_cfg.get("thresholds", {})

        # Image ratio (stricter for Microsoft)
        ms_img_max = ms_thresholds.get("image_text_ratio_max", 0.40)
        if image_text_ratio > ms_img_max:
            ms_profile.flags.append(
                ISPFlag(
                    isp="microsoft",
                    category="structural",
                    severity="warning",
                    description=(
                        f"Image-to-text ratio is {image_text_ratio:.0%} "
                        f"(Microsoft threshold: {ms_img_max:.0%} for new senders)."
                    ),
                    threshold=f"image_text_ratio_max: {ms_img_max:.0%}",
                    fix="Add more text content. Microsoft is stricter for new sender domains.",
                )
            )
            ms_profile.score -= 15

        # SmartScreen
        smartscreen_flags = _analyze_microsoft_smartscreen(doc, ms_cfg)
        ms_profile.flags.extend(smartscreen_flags)
        for flag in smartscreen_flags:
            ms_profile.score -= 10 if flag.severity == "error" else 5

        ms_profile.score = max(0, ms_profile.score)
        ms_profile.risk_level = _score_to_risk(ms_profile.score)
        isp_risks["microsoft"] = ms_profile

    # Yahoo/AOL
    yahoo_cfg = isps_config.get("yahoo", {})
    if yahoo_cfg:
        yahoo_profile = ISPRiskProfile(
            isp="yahoo",
            display_name=yahoo_cfg.get("display_name", "Yahoo / AOL"),
        )
        yahoo_thresholds = yahoo_cfg.get("thresholds", {})

        # Link density (Yahoo is sensitive)
        yahoo_link_max = yahoo_thresholds.get("link_density_max", 3.0)
        if link_density > yahoo_link_max:
            yahoo_profile.flags.append(
                ISPFlag(
                    isp="yahoo",
                    category="structural",
                    severity="warning",
                    description=(
                        f"Link density is {link_density:.1f} per 100 words "
                        f"(Yahoo/AOL threshold: {yahoo_link_max})."
                    ),
                    threshold=f"link_density_max: {yahoo_link_max}",
                    fix="Reduce links to fewer than 3 per 100 words.",
                )
            )
            yahoo_profile.score -= 10

        # Reputation signals
        yahoo_flags = _analyze_yahoo_reputation(doc, yahoo_cfg)
        yahoo_profile.flags.extend(yahoo_flags)
        for flag in yahoo_flags:
            yahoo_profile.score -= 8 if flag.severity == "warning" else 3

        yahoo_profile.score = max(0, yahoo_profile.score)
        yahoo_profile.risk_level = _score_to_risk(yahoo_profile.score)
        isp_risks["yahoo"] = yahoo_profile

    # --- Cross-ISP structural checks ---
    structural_flags: list[str] = []

    cross_domain_flags = _check_cross_domain_images(doc)
    responsive_flags = _check_responsive_design(doc, html)
    tracking_flags = _check_tracking_params(doc)

    all_structural = cross_domain_flags + responsive_flags + tracking_flags
    for flag in all_structural:
        structural_flags.append(f"[{flag.severity}] {flag.description}")
        # Add to all ISP profiles
        for profile in isp_risks.values():
            profile.flags.append(flag)
            profile.score = max(0, profile.score - (5 if flag.severity == "warning" else 2))
            profile.risk_level = _score_to_risk(profile.score)

    # Hidden text flags add to structural
    for hf in hidden_flags:
        structural_flags.append(f"[error] {hf.description}")

    # --- Overall risk ---
    worst_risk = "low"
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    for profile in isp_risks.values():
        if risk_order.get(profile.risk_level, 0) > risk_order.get(worst_risk, 0):
            worst_risk = profile.risk_level
    if len(hidden_flags) >= 2:
        worst_risk = "critical"
    elif len(hidden_flags) == 1 and risk_order.get(worst_risk, 0) < 2:
        worst_risk = "high"

    # Auth readiness estimate (0-25 scale, matching existing dimension)
    auth_score = 25
    unsub_re = re.compile(r"unsubscribe|opt[\s-]?out", re.IGNORECASE)
    has_unsub = any(
        unsub_re.search(link.get("href") or "") or unsub_re.search(link.text_content() or "")
        for link in doc.xpath("//a[@href]")
    )
    if not has_unsub:
        auth_score -= 12

    list_unsub_re = re.compile(r"list-unsubscribe", re.IGNORECASE)
    if not list_unsub_re.search(html):
        auth_score -= 8

    address_patterns = (
        re.compile(
            r"\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd)",
            re.IGNORECASE,
        ),
        re.compile(r"p\.?\s*o\.?\s*box\s+\d+", re.IGNORECASE),
    )
    if not any(p.search(text_content) for p in address_patterns):
        auth_score -= 5

    return DeliverabilityAnalysis(
        image_text_ratio=round(image_text_ratio, 3),
        link_density=round(link_density, 2),
        hidden_content_count=len(hidden_flags),
        auth_readiness_score=max(0, auth_score),
        isp_risks=isp_risks,
        structural_flags=structural_flags,
        overall_risk=worst_risk,
        gmail_promo_tab_score=promo_score,
    )
