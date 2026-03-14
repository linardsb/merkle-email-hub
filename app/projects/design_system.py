"""Design system models for per-project brand identity."""

from __future__ import annotations

import re
from typing import Any, Literal

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

    palette: BrandPalette
    typography: Typography = Field(default_factory=Typography)
    logo: LogoConfig | None = None
    footer: FooterConfig | None = None
    social_links: tuple[SocialLink, ...] = ()
    button_border_radius: str = Field(default="4px", pattern=r"^\d+px$")
    button_style: Literal["filled", "outlined", "text"] = "filled"


def load_design_system(raw: dict[str, Any] | None) -> DesignSystem | None:
    """Parse a design system from the JSON column value.

    Returns None if raw is None or empty.
    """
    if not raw:
        return None
    return DesignSystem.model_validate(raw)


def design_system_to_brand_rules(ds: DesignSystem) -> dict[str, Any]:
    """Convert a DesignSystem to brand_compliance params format.

    Returns dict with keys matching BrandComplianceCheck config params:
    allowed_colors, required_fonts, required_elements.
    """
    # Collect all non-None palette colors, deduplicate preserving order
    seen: set[str] = set()
    unique_colors: list[str] = []
    for field_name in BrandPalette.model_fields:
        val = getattr(ds.palette, field_name)
        if val is not None and val not in seen:
            seen.add(val)
            unique_colors.append(val)

    # Extract primary font from CSS font stack (first entry before comma)
    fonts: list[str] = []
    for font_stack in [ds.typography.heading_font, ds.typography.body_font]:
        primary = font_stack.split(",")[0].strip().strip("'\"")
        if primary and primary not in fonts:
            fonts.append(primary)

    # Required elements from footer/logo presence
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
