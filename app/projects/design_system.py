"""Design system models for per-project brand identity."""

from __future__ import annotations

import re
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_HTTPS_OR_DATA_RE = re.compile(r"^(https://|data:image/)")


def _validate_hex_color(v: str) -> str:
    if not _HEX_COLOR_RE.match(v):
        msg = f"Invalid hex color: {v}. Must be #RRGGBB format."
        raise ValueError(msg)
    return v.lower()


class BrandPalette(BaseModel):
    """Brand color palette — all hex #RRGGBB."""

    model_config = ConfigDict(frozen=True)

    primary: str
    secondary: str
    accent: str
    background: str = "#ffffff"
    text: str = "#000000"
    link: str = "#0000ee"
    dark_background: str | None = None
    dark_text: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_colors(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return _validate_hex_color(v)
        return v


class Typography(BaseModel):
    """Brand typography — CSS font stacks."""

    model_config = ConfigDict(frozen=True)

    heading_font: str = Field(
        default="Arial, Helvetica, sans-serif",
        min_length=1,
        max_length=500,
    )
    body_font: str = Field(
        default="Arial, Helvetica, sans-serif",
        min_length=1,
        max_length=500,
    )
    base_size: str = Field(default="16px", pattern=r"^\d+px$")
    heading_line_height: str | None = Field(default=None, pattern=r"^\d+px$")
    body_line_height: str | None = Field(default=None, pattern=r"^\d+px$")
    heading_letter_spacing: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?px$")
    body_letter_spacing: str | None = Field(default=None, pattern=r"^-?\d+(\.\d+)?px$")
    heading_text_transform: str | None = Field(
        default=None, pattern=r"^(uppercase|lowercase|capitalize)$"
    )


class LogoConfig(BaseModel):
    """Logo configuration."""

    model_config = ConfigDict(frozen=True)

    url: str = Field(..., min_length=1, max_length=2000)
    alt_text: str = Field(..., min_length=1, max_length=200)
    width: int = Field(..., ge=1, le=2000)
    height: int = Field(..., ge=1, le=2000)

    @field_validator("url")
    @classmethod
    def validate_logo_url(cls, v: str) -> str:
        if not _HTTPS_OR_DATA_RE.match(v):
            msg = "Logo URL must be HTTPS or a data: URI"
            raise ValueError(msg)
        return v


class FooterConfig(BaseModel):
    """Footer content configuration."""

    model_config = ConfigDict(frozen=True)

    company_name: str = Field(..., min_length=1, max_length=200)
    legal_text: str = Field(default="", max_length=2000)
    address: str = Field(default="", max_length=500)
    unsubscribe_text: str = Field(default="Unsubscribe", max_length=200)


class SocialLink(BaseModel):
    """Social media link."""

    model_config = ConfigDict(frozen=True)

    platform: Literal[
        "facebook",
        "twitter",
        "instagram",
        "linkedin",
        "youtube",
        "tiktok",
        "pinterest",
        "threads",
    ]
    url: str = Field(..., min_length=1, max_length=500)
    icon_url: str | None = Field(default=None, max_length=2000)

    @field_validator("url")
    @classmethod
    def validate_social_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            msg = "Social link URL must be HTTPS"
            raise ValueError(msg)
        return v

    @field_validator("icon_url")
    @classmethod
    def validate_icon_url(cls, v: str | None) -> str | None:
        if v is not None and not _HTTPS_OR_DATA_RE.match(v):
            msg = "Icon URL must be HTTPS or a data: URI"
            raise ValueError(msg)
        return v


class DesignSystem(BaseModel):
    """Complete per-project design system."""

    model_config = ConfigDict(frozen=True)

    # Structured fields (existing — backward compat for API/frontend)
    palette: BrandPalette
    typography: Typography = Field(default_factory=Typography)
    logo: LogoConfig | None = None
    footer: FooterConfig | None = None
    social_links: tuple[SocialLink, ...] = ()
    button_border_radius: str = Field(default="4px", pattern=r"^\d+px$")
    button_style: Literal["filled", "outlined", "text"] = "filled"

    # Dynamic token maps (pipeline reads these)
    # When populated, these are authoritative. When empty, derived from structured fields.
    colors: dict[str, str] = Field(default_factory=dict)
    fonts: dict[str, str] = Field(default_factory=dict)
    font_sizes: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, str] = Field(default_factory=dict)

    @field_validator("colors", mode="before")
    @classmethod
    def validate_color_values(cls, v: object) -> object:
        if not isinstance(v, dict):
            return v
        raw: dict[str, str] = {}
        for key, color in cast(dict[str, object], v).items():
            if not isinstance(color, str):
                msg = f"Color value for role '{key}' must be a string, got {type(color).__name__}"
                raise ValueError(msg)
            _validate_hex_color(color)
            raw[str(key)] = color.lower()
        return raw


def load_design_system(raw: dict[str, Any] | None) -> DesignSystem | None:
    """Parse a design system from the JSON column value.

    Returns None if raw is None or empty.
    """
    if not raw:
        return None
    return DesignSystem.model_validate(raw)


def resolve_color_map(ds: DesignSystem) -> dict[str, str]:
    """Build the complete role->hex color map for pipeline use.

    Merges BrandPalette fields (as base roles) with explicit colors dict
    (which can override or add roles). Works for any client:
    - Simple client: only BrandPalette filled -> auto-derived roles
    - Advanced client: colors dict with custom roles
    - Figma import: colors dict populated directly from design tool tokens
    """
    base: dict[str, str] = {}
    for field_name in BrandPalette.model_fields:
        val = getattr(ds.palette, field_name)
        if val is not None:
            base[field_name] = val

    # Auto-derive common aliases from BrandPalette
    if "primary" in base:
        base.setdefault("cta", base["primary"])
    if "text" in base:
        base.setdefault("heading", base["text"])
    if "accent" in base:
        base.setdefault("cta", base["accent"])

    # Merge explicit colors dict (overrides base)
    base.update(ds.colors)
    return base


def resolve_font_map(ds: DesignSystem) -> dict[str, str]:
    """Build role->font-stack map."""
    base: dict[str, str] = {
        "heading": ds.typography.heading_font,
        "body": ds.typography.body_font,
    }
    base.update(ds.fonts)
    return base


def resolve_font_size_map(ds: DesignSystem) -> dict[str, str]:
    """Build role->font-size map."""
    base: dict[str, str] = {"base": ds.typography.base_size}
    base.update(ds.font_sizes)
    return base


def resolve_spacing_map(ds: DesignSystem) -> dict[str, str]:
    """Build role->spacing map."""
    base: dict[str, str] = {"border_radius": ds.button_border_radius}
    base.update(ds.spacing)
    return base


def design_system_to_brand_rules(ds: DesignSystem) -> dict[str, Any]:
    """Convert a DesignSystem to brand_compliance params format.

    Returns dict with keys matching BrandComplianceCheck config params:
    allowed_colors, required_fonts, required_elements.
    """
    all_colors = resolve_color_map(ds)
    unique_colors = list(dict.fromkeys(all_colors.values()))

    font_map = resolve_font_map(ds)
    fonts: list[str] = []
    for stack in font_map.values():
        primary = stack.split(",")[0].strip().strip("'\"")
        if primary and primary not in fonts:
            fonts.append(primary)

    required_elements: list[str] = []
    if ds.footer:
        required_elements.append("footer")
    if ds.logo:
        required_elements.append("logo")

    return {
        "allowed_colors": unique_colors,
        "required_fonts": fonts,
        "required_elements": required_elements,
    }
