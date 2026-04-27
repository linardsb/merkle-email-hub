"""E2E: design system → repair pipeline → brand compliance QA gate."""

import pytest

from app.projects.design_system import (
    BrandPalette,
    DesignSystem,
    FooterConfig,
    LogoConfig,
)
from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.checks._factory import get_check
from app.qa_engine.repair import RepairPipeline


def _make_ds() -> DesignSystem:
    return DesignSystem(
        palette=BrandPalette(
            primary="#e60012",
            secondary="#1a1a1a",
            accent="#ff6600",
        ),
        footer=FooterConfig(company_name="TestCorp", legal_text="© 2026"),
        logo=LogoConfig(
            url="https://example.com/logo.png",
            alt_text="TestCorp",
            width=200,
            height=50,
        ),
    )


# Simulates LLM output with off-brand colors and missing elements
_OFF_BRAND_HTML = """<!DOCTYPE html>
<html><head><style>
  .header { background-color: #336699; color: #ffffff; }
  .cta { background-color: #22aa44; }
</style></head>
<body>
  <div class="header"><h1>Campaign</h1></div>
  <p style="color: #333333;">Content here</p>
  <a class="cta" href="#">Buy Now</a>
</body></html>"""


class TestE2EBrandEnforcement:
    @pytest.mark.anyio
    async def test_repair_then_qa_passes(self) -> None:
        """Off-brand HTML → repair pipeline corrects → brand compliance passes."""
        ds = _make_ds()

        # Run repair with design system
        pipeline = RepairPipeline(design_system=ds)
        repaired = pipeline.run(_OFF_BRAND_HTML)

        # Off-palette colors should be corrected
        assert "#336699" not in repaired.html
        assert "#22aa44" not in repaired.html

        # Footer and logo should be injected
        assert "<footer" in repaired.html
        assert "TestCorp" in repaired.html
        assert "logo.png" in repaired.html

        # Brand compliance check should pass on repaired HTML
        check = get_check("brand_compliance")
        config = QACheckConfig(
            enabled=True,
            params={"_design_system": ds.model_dump()},
        )
        result = await check.run(repaired.html, config)
        assert result.passed, f"Brand compliance failed: {result.details}"

    @pytest.mark.anyio
    async def test_already_compliant_html_is_noop(self) -> None:
        """On-brand HTML passes through repair unchanged."""
        ds = _make_ds()
        compliant = """<!DOCTYPE html>
<html><head></head><body>
  <div style="text-align:center;"><img src="https://example.com/logo.png" alt="TestCorp" width="200" height="50" /></div>
  <h1 style="color: #e60012;">Hello</h1>
  <p style="color: #1a1a1a;">Content</p>
  <footer><p>TestCorp</p><p>© 2026</p></footer>
</body></html>"""

        pipeline = RepairPipeline(design_system=ds)
        repaired = pipeline.run(compliant)

        # No brand repairs should be applied (other stages may apply structural fixes)
        brand_repairs = [
            r for r in repaired.repairs_applied if r.startswith(("color_", "injected_"))
        ]
        assert brand_repairs == []

    @pytest.mark.anyio
    async def test_no_design_system_is_noop(self) -> None:
        """Without design system, brand repair is skipped entirely."""
        pipeline = RepairPipeline(design_system=None)
        repaired = pipeline.run(_OFF_BRAND_HTML)

        # Off-palette colors remain (no brand repair)
        assert "#336699" in repaired.html

    @pytest.mark.anyio
    async def test_idempotent(self) -> None:
        """Running repair twice on same HTML produces identical output."""
        ds = _make_ds()
        pipeline = RepairPipeline(design_system=ds)
        r1 = pipeline.run(_OFF_BRAND_HTML)
        r2 = pipeline.run(r1.html)

        assert r1.html == r2.html
        brand_repairs_r2 = [r for r in r2.repairs_applied if r.startswith(("color_", "injected_"))]
        assert brand_repairs_r2 == []
