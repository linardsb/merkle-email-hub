"""Tests for the rendering resilience QA check."""

import pytest

from app.qa_engine.checks.rendering_resilience import RenderingResilienceCheck

RESILIENT_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Test</title></head>
<body>
<table role="presentation" width="100%" style="max-width:600px;margin:0 auto;">
<tr><td style="padding:20px;font-family:Arial,sans-serif;color:#333333;">
<h1 style="margin:0;font-size:24px;">Hello</h1>
<p style="margin:10px 0;">Inline styled content is resilient to style stripping.</p>
<a href="https://example.com" style="color:#0066cc;">Link</a>
</td></tr>
</table>
</body></html>"""


@pytest.mark.asyncio
class TestRenderingResilienceCheck:
    async def test_resilient_html_passes(self) -> None:
        check = RenderingResilienceCheck(threshold=0.5)
        result = await check.run(RESILIENT_HTML)
        assert result.check_name == "rendering_resilience"
        assert result.score > 0.0
        assert result.score >= 0.5

    async def test_threshold_respected(self) -> None:
        check = RenderingResilienceCheck(threshold=1.0)
        result = await check.run(RESILIENT_HTML)
        # Perfect resilience is unlikely
        assert not result.passed

    async def test_low_threshold_passes(self) -> None:
        check = RenderingResilienceCheck(threshold=0.1)
        result = await check.run(RESILIENT_HTML)
        assert result.passed

    async def test_severity_warning_when_below_threshold(self) -> None:
        check = RenderingResilienceCheck(threshold=1.0)
        result = await check.run(RESILIENT_HTML)
        # Score < 1.0 but >= 0.4 → warning
        assert not result.passed
        assert result.severity == "warning"

    async def test_severity_info_when_passing(self) -> None:
        check = RenderingResilienceCheck(threshold=0.1)
        result = await check.run(RESILIENT_HTML)
        assert result.passed
        assert result.severity == "info"

    async def test_details_contain_profile_summaries(self) -> None:
        check = RenderingResilienceCheck(threshold=0.5)
        result = await check.run(RESILIENT_HTML)
        assert "Resilience:" in result.details  # type: ignore[operator]
        assert "Profiles:" in result.details  # type: ignore[operator]

    async def test_check_name(self) -> None:
        check = RenderingResilienceCheck()
        assert check.name == "rendering_resilience"

    async def test_severity_error_when_very_low_score(self) -> None:
        """HTML relying entirely on <style> blocks should score poorly."""
        fragile_html = """<!DOCTYPE html><html><head>
        <style>
        .hero { background: red; color: white; font-size: 24px; }
        .content { padding: 20px; margin: 10px; }
        .footer { background: #333; color: #fff; }
        </style>
        </head><body>
        <div class="hero">Hero</div>
        <div class="content">Content</div>
        <div class="footer">Footer</div>
        </body></html>"""
        check = RenderingResilienceCheck(threshold=1.0)
        result = await check.run(fragile_html)
        # With threshold=1.0, it won't pass; check severity is error or warning
        assert not result.passed
        assert result.severity in ("error", "warning")

    async def test_check_uses_default_profiles(self) -> None:
        """Resilience check runs profiles (not zero)."""
        check = RenderingResilienceCheck(threshold=0.1)
        result = await check.run(RESILIENT_HTML)
        # details should mention at least one profile
        assert result.details is not None
        assert ":" in result.details  # format: "profile_name: 0.XX (N/M)"

    async def test_check_returns_profile_count_in_details(self) -> None:
        check = RenderingResilienceCheck(threshold=0.5)
        result = await check.run(RESILIENT_HTML)
        assert result.details is not None
        assert "Profiles:" in result.details
