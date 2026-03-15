"""Unit tests for BrandRepair stage."""

from typing import Any

from app.projects.design_system import BrandPalette, DesignSystem, FooterConfig, LogoConfig
from app.qa_engine.repair.brand import BrandRepair, _find_nearest_palette_color, _hex_to_rgb


class TestColorDistance:
    def test_hex_to_rgb(self) -> None:
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)
        assert _hex_to_rgb("#00ff00") == (0, 255, 0)

    def test_exact_match(self) -> None:
        result = _find_nearest_palette_color("#ff0000", ["#ff0000", "#00ff00"])
        assert result == "#ff0000"

    def test_nearest_match(self) -> None:
        # #fe0000 is closest to #ff0000
        result = _find_nearest_palette_color("#fe0000", ["#ff0000", "#00ff00", "#0000ff"])
        assert result == "#ff0000"

    def test_empty_palette(self) -> None:
        assert _find_nearest_palette_color("#ff0000", []) is None


def _make_ds(**kwargs: Any) -> DesignSystem:
    defaults: dict[str, Any] = {
        "palette": BrandPalette(primary="#ff0000", secondary="#00ff00", accent="#0000ff"),
    }
    defaults.update(kwargs)
    return DesignSystem(**defaults)


class TestBrandRepairColors:
    def test_replaces_off_palette_color(self) -> None:
        ds = _make_ds()
        stage = BrandRepair(ds)
        html = '<div style="color: #fe0101;">text</div>'
        result = stage.repair(html)
        assert "#fe0101" not in result.html
        assert len(result.repairs_applied) == 1

    def test_preserves_on_palette_color(self) -> None:
        ds = _make_ds()
        stage = BrandRepair(ds)
        html = '<div style="color: #ff0000;">text</div>'
        result = stage.repair(html)
        assert "#ff0000" in result.html
        assert result.repairs_applied == []

    def test_no_op_without_design_system(self) -> None:
        stage = BrandRepair(None)
        html = '<div style="color: #abcdef;">text</div>'
        result = stage.repair(html)
        assert result.html == html
        assert result.repairs_applied == []

    def test_idempotent(self) -> None:
        ds = _make_ds()
        stage = BrandRepair(ds)
        html = '<div style="color: #fe0101;">text</div>'
        r1 = stage.repair(html)
        r2 = stage.repair(r1.html)
        assert r1.html == r2.html
        assert r2.repairs_applied == []


class TestBrandRepairFooter:
    def test_injects_footer_when_missing(self) -> None:
        ds = _make_ds(footer=FooterConfig(company_name="Acme Inc"))
        stage = BrandRepair(ds)
        html = "<!DOCTYPE html><html><head></head><body><p>Hi</p></body></html>"
        result = stage.repair(html)
        assert "Acme Inc" in result.html
        assert "<footer" in result.html
        assert "injected_footer" in result.repairs_applied

    def test_no_inject_when_footer_exists(self) -> None:
        ds = _make_ds(footer=FooterConfig(company_name="Acme Inc"))
        stage = BrandRepair(ds)
        html = '<body><footer class="footer">existing</footer></body>'
        result = stage.repair(html)
        assert "injected_footer" not in result.repairs_applied

    def test_no_inject_when_no_footer_config(self) -> None:
        ds = _make_ds()
        stage = BrandRepair(ds)
        html = "<body><p>Hi</p></body>"
        result = stage.repair(html)
        assert "<footer" not in result.html


class TestBrandRepairLogo:
    def test_injects_logo_when_missing(self) -> None:
        ds = _make_ds(
            logo=LogoConfig(
                url="https://example.com/logo.png", alt_text="Logo", width=200, height=50
            )
        )
        stage = BrandRepair(ds)
        html = "<!DOCTYPE html><html><head></head><body><p>Hi</p></body></html>"
        result = stage.repair(html)
        assert "https://example.com/logo.png" in result.html
        assert "injected_logo" in result.repairs_applied

    def test_no_inject_when_logo_exists(self) -> None:
        ds = _make_ds(
            logo=LogoConfig(
                url="https://example.com/logo.png", alt_text="Logo", width=200, height=50
            )
        )
        stage = BrandRepair(ds)
        html = '<body><img src="img.png" alt="Company logo" /></body>'
        result = stage.repair(html)
        assert "injected_logo" not in result.repairs_applied
