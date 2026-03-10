"""Map Can I Email data to ontology types."""

from __future__ import annotations

from app.knowledge.ontology.sync.schemas import CanIEmailFeature
from app.knowledge.ontology.types import (
    CSSCategory,
    CSSProperty,
    SupportLevel,
)

# --- Client ID mapping ---
# Maps (family, platform) → our client_id.
CLIENT_MAP: dict[tuple[str, str], str] = {
    ("apple-mail", "macos"): "apple_mail_macos",
    ("apple-mail", "ios"): "apple_mail_ios",
    ("gmail", "desktop-webmail"): "gmail_web",
    ("gmail", "ios"): "gmail_ios",
    ("gmail", "android"): "gmail_android",
    ("gmail", "mobile-webmail"): "gmail_mobile_web",
    ("outlook", "windows"): "outlook_2019_win",
    ("outlook", "windows-mail"): "outlook_windows_mail",
    ("outlook", "macos"): "outlook_macos",
    ("outlook", "outlook-com"): "outlook_com",
    ("outlook", "ios"): "outlook_ios",
    ("outlook", "android"): "outlook_android",
    ("yahoo", "desktop-webmail"): "yahoo_web",
    ("yahoo", "ios"): "yahoo_ios",
    ("yahoo", "android"): "yahoo_android",
    ("samsung-email", "android"): "samsung_mail_14",
    ("thunderbird", "macos"): "thunderbird_macos",
    ("thunderbird", "windows"): "thunderbird_win",
    ("aol", "desktop-webmail"): "aol_web",
    ("protonmail", "desktop-webmail"): "protonmail_web",
    ("protonmail", "ios"): "protonmail_ios",
    ("protonmail", "android"): "protonmail_android",
    ("hey", "desktop-webmail"): "hey_web",
    ("fastmail", "desktop-webmail"): "fastmail_web",
    ("mail-ru", "desktop-webmail"): "mail_ru_web",
}

# --- CSS category inference ---
CATEGORY_MAP: dict[str, CSSCategory] = {
    "display": CSSCategory.LAYOUT,
    "position": CSSCategory.LAYOUT,
    "float": CSSCategory.LAYOUT,
    "overflow": CSSCategory.LAYOUT,
    "width": CSSCategory.BOX_MODEL,
    "height": CSSCategory.BOX_MODEL,
    "margin": CSSCategory.BOX_MODEL,
    "padding": CSSCategory.BOX_MODEL,
    "font": CSSCategory.TYPOGRAPHY,
    "text": CSSCategory.TYPOGRAPHY,
    "letter": CSSCategory.TYPOGRAPHY,
    "word": CSSCategory.TYPOGRAPHY,
    "line": CSSCategory.TYPOGRAPHY,
    "color": CSSCategory.COLOR_BACKGROUND,
    "background": CSSCategory.COLOR_BACKGROUND,
    "border": CSSCategory.BORDER_SHADOW,
    "box-shadow": CSSCategory.BORDER_SHADOW,
    "outline": CSSCategory.BORDER_SHADOW,
    "transform": CSSCategory.TRANSFORM_ANIMATION,
    "animation": CSSCategory.TRANSFORM_ANIMATION,
    "transition": CSSCategory.TRANSFORM_ANIMATION,
    "flex": CSSCategory.FLEXBOX,
    "align": CSSCategory.FLEXBOX,
    "justify": CSSCategory.FLEXBOX,
    "grid": CSSCategory.GRID,
    "gap": CSSCategory.GRID,
    "@media": CSSCategory.MEDIA_QUERY,
    "prefers-color-scheme": CSSCategory.DARK_MODE,
    "table": CSSCategory.TABLE,
    "list": CSSCategory.LIST,
}


def map_support_value(value: str) -> SupportLevel:
    """Map Can I Email support char to our SupportLevel enum."""
    v = value.strip().lower()
    if v.startswith("y"):
        return SupportLevel.FULL
    if v.startswith("a"):
        return SupportLevel.PARTIAL
    if v.startswith("n"):
        return SupportLevel.NONE
    return SupportLevel.UNKNOWN


def resolve_client_id(family: str, platform: str) -> str | None:
    """Resolve a Can I Email (family, platform) to our client_id."""
    return CLIENT_MAP.get((family, platform))


def feature_to_property_id(slug: str) -> str:
    """Convert Can I Email slug to our property_id format.

    Examples:
        css-display-flex → display_flex
        html-video → html_video
    """
    prop_id = slug
    for prefix in ("css-", "html-"):
        if prop_id.startswith(prefix):
            prop_id = prop_id[len(prefix) :]
            break
    return prop_id.replace("-", "_")


def infer_category(slug: str, title: str) -> CSSCategory:
    """Infer CSSCategory from slug/title."""
    text = f"{slug} {title}".lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in text:
            return cat
    return CSSCategory.OTHER


def extract_property_name_value(title: str) -> tuple[str, str | None]:
    """Extract CSS property name and optional value from title.

    Examples:
        "display:flex" → ("display", "flex")
        "background-color" → ("background-color", None)
    """
    if ":" in title:
        parts = title.split(":", 1)
        return parts[0].strip(), parts[1].strip() or None
    return title.strip(), None


def feature_to_css_property(feature: CanIEmailFeature) -> CSSProperty:
    """Convert a CanIEmailFeature to a CSSProperty."""
    prop_name, value = extract_property_name_value(feature.title)
    return CSSProperty(
        id=feature_to_property_id(feature.slug),
        property_name=prop_name,
        value=value,
        category=infer_category(feature.slug, feature.title),
        description=f"From Can I Email ({feature.last_test_date})",
        tags=("caniemail", feature.category),
    )


def feature_to_support_entries(
    feature: CanIEmailFeature,
) -> list[tuple[str, str, SupportLevel, str]]:
    """Extract (property_id, client_id, level, notes) from a feature's stats.

    Uses the LATEST version entry per (family, platform) as the current support level.
    """
    prop_id = feature_to_property_id(feature.slug)
    entries: list[tuple[str, str, SupportLevel, str]] = []

    for family, platforms in feature.stats.items():
        for platform, versions in platforms.items():
            client_id = resolve_client_id(family, platform)
            if client_id is None:
                continue

            if not versions:
                continue

            # Use the last (latest) version entry
            # Keys may be int/float from YAML (e.g., 2019, 12.4)
            latest_version = list(versions.keys())[-1]
            raw_value = str(versions[latest_version])

            level = map_support_value(raw_value)

            # Extract note reference if present (e.g., "a #1")
            note = ""
            if "#" in raw_value:
                note_num = raw_value.split("#", 1)[1].strip()
                note = feature.notes.get(note_num, "")

            entries.append((prop_id, client_id, level, note))

    return entries
