# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportCallIssue=false
# mypy: disable-error-code="method-assign"
"""Tests for design system models, bridge function, and service methods."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.projects.design_system import (
    BrandPalette,
    DesignSystem,
    FooterConfig,
    LogoConfig,
    SocialLink,
    Typography,
    design_system_to_brand_rules,
    load_design_system,
)
from app.projects.service import ProjectService

# ── Model validation ──


class TestBrandPalette:
    def test_valid_palette(self) -> None:
        p = BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
        assert p.primary == "#ff0000"

    def test_normalises_to_lowercase(self) -> None:
        p = BrandPalette(primary="#FF0000", secondary="#00FF00", accent="#0000FF")
        assert p.primary == "#ff0000"

    def test_rejects_invalid_hex(self) -> None:
        with pytest.raises(ValidationError):
            BrandPalette(primary="red", secondary="#00ff00", accent="#0000ff")

    def test_rejects_short_hex(self) -> None:
        with pytest.raises(ValidationError):
            BrandPalette(primary="#fff", secondary="#00ff00", accent="#0000ff")


class TestLogoConfig:
    def test_https_url_valid(self) -> None:
        logo = LogoConfig(url="https://example.com/logo.png", alt_text="Logo", width=200, height=50)
        assert logo.url == "https://example.com/logo.png"

    def test_data_uri_valid(self) -> None:
        logo = LogoConfig(url="data:image/png;base64,abc123", alt_text="Logo", width=200, height=50)
        assert logo.url.startswith("data:image/")

    def test_http_url_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LogoConfig(url="http://example.com/logo.png", alt_text="Logo", width=200, height=50)


class TestSocialLink:
    def test_valid_link(self) -> None:
        link = SocialLink(platform="twitter", url="https://twitter.com/test")
        assert link.platform == "twitter"

    def test_invalid_platform_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SocialLink(platform="myspace", url="https://myspace.com/test")  # pyright: ignore[reportArgumentType]


class TestDesignSystem:
    def test_minimal_design_system(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
        )
        assert ds.typography.heading_font == "Arial, Helvetica, sans-serif"
        assert ds.button_style == "filled"

    def test_frozen(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
        )
        with pytest.raises(ValidationError):
            ds.button_style = "outlined"  # type: ignore[misc]


# ── load_design_system ──


class TestLoadDesignSystem:
    def test_none_returns_none(self) -> None:
        assert load_design_system(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert load_design_system({}) is None

    def test_valid_dict_returns_design_system(self) -> None:
        raw: dict[str, Any] = {
            "palette": {"primary": "#ff0000", "secondary": "#00ff00", "accent": "#0000ff"}
        }
        ds = load_design_system(raw)
        assert ds is not None
        assert ds.palette.primary == "#ff0000"

    def test_invalid_dict_raises(self) -> None:
        with pytest.raises(ValidationError):
            load_design_system({"palette": {"primary": "not-a-color"}})


# ── design_system_to_brand_rules ──


class TestDesignSystemToBrandRules:
    def test_colors_extracted(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
        )
        rules = design_system_to_brand_rules(ds)
        assert "#ff0000" in rules["allowed_colors"]
        assert "#00ff00" in rules["allowed_colors"]
        assert "#0000ff" in rules["allowed_colors"]

    def test_fonts_extracted(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff"),
            typography=Typography(
                heading_font="Roboto, sans-serif", body_font="Open Sans, sans-serif"
            ),
        )
        rules = design_system_to_brand_rules(ds)
        assert "Roboto" in rules["required_fonts"]
        assert "Open Sans" in rules["required_fonts"]

    def test_required_elements_from_footer_and_logo(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff"),
            footer=FooterConfig(company_name="Test Corp"),
            logo=LogoConfig(
                url="https://example.com/logo.png", alt_text="Logo", width=200, height=50
            ),
        )
        rules = design_system_to_brand_rules(ds)
        assert "footer" in rules["required_elements"]
        assert "logo" in rules["required_elements"]

    def test_no_footer_no_logo(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
        )
        rules = design_system_to_brand_rules(ds)
        assert rules["required_elements"] == []

    def test_dark_mode_colors_included(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(
                primary="#ff0000",
                secondary="#00ff00",
                accent="#0000ff",
                dark_background="#1a1a1a",
                dark_text="#ffffff",
            ),
        )
        rules = design_system_to_brand_rules(ds)
        assert "#1a1a1a" in rules["allowed_colors"]
        assert "#ffffff" in rules["allowed_colors"]

    def test_deduplicates_colors(self) -> None:
        ds = DesignSystem(
            palette=BrandPalette(
                primary="#ff0000",
                secondary="#ff0000",
                accent="#ff0000",
            ),
        )
        rules = design_system_to_brand_rules(ds)
        assert rules["allowed_colors"].count("#ff0000") == 1


# ── Service methods (mocked DB) ──


def _make_project(design_system: dict[str, Any] | None = None) -> MagicMock:
    project = MagicMock()
    project.id = 1
    project.name = "Test"
    project.description = None
    project.status = "active"
    project.client_org_id = 1
    project.created_by_id = 1
    project.is_active = True
    project.deleted_at = None
    project.target_clients = None
    project.qa_profile = None
    project.design_system = design_system
    project.template_config = None
    project.created_at = "2026-01-01T00:00:00Z"
    project.updated_at = "2026-01-01T00:00:00Z"
    return project


def _make_admin() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.role = "admin"
    return user


@pytest.fixture
def service() -> ProjectService:
    mock_db = AsyncMock()
    svc = ProjectService(mock_db)
    svc.projects = AsyncMock()
    svc.orgs = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_get_design_system_returns_none_when_unset(service: ProjectService) -> None:
    service.projects.get = AsyncMock(return_value=_make_project())
    service.projects.get_member = AsyncMock(return_value=MagicMock())
    result = await service.get_design_system(1, _make_admin())
    assert result is None


@pytest.mark.asyncio
async def test_get_design_system_returns_parsed(service: ProjectService) -> None:
    raw: dict[str, Any] = {
        "palette": {"primary": "#ff0000", "secondary": "#00ff00", "accent": "#0000ff"}
    }
    service.projects.get = AsyncMock(return_value=_make_project(design_system=raw))
    service.projects.get_member = AsyncMock(return_value=MagicMock())
    result = await service.get_design_system(1, _make_admin())
    assert result is not None
    assert result.palette.primary == "#ff0000"


@pytest.mark.asyncio
async def test_update_design_system_stores_json(service: ProjectService) -> None:
    service.projects.get = AsyncMock(return_value=_make_project())
    service.projects.get_member = AsyncMock(return_value=MagicMock())
    service.projects.update_design_system = AsyncMock(return_value=_make_project())
    ds = DesignSystem(
        palette=BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff")
    )
    result = await service.update_design_system(1, ds, _make_admin())
    assert result.palette.primary == "#ff0000"
    service.projects.update_design_system.assert_called_once()


@pytest.mark.asyncio
async def test_delete_design_system(service: ProjectService) -> None:
    service.projects.get = AsyncMock(return_value=_make_project())
    service.projects.get_member = AsyncMock(return_value=MagicMock())
    service.projects.update_design_system = AsyncMock(return_value=_make_project())
    await service.delete_design_system(1, _make_admin())
    service.projects.update_design_system.assert_called_once()
    call_args = service.projects.update_design_system.call_args
    assert call_args[0][1] is None  # second positional arg is design_system=None
