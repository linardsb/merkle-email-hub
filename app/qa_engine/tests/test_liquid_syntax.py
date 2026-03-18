"""Tests for 24B.5 — Liquid Template Dry-Run Validation."""

from __future__ import annotations

import pytest

from app.qa_engine.check_config import QACheckConfig
from app.qa_engine.checks.liquid_syntax import LiquidSyntaxCheck


@pytest.fixture
def check() -> LiquidSyntaxCheck:
    return LiquidSyntaxCheck()


class TestLiquidSyntaxCheck:
    """Tests for the Liquid syntax QA check."""

    @pytest.mark.asyncio
    async def test_valid_liquid_passes(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        <p>Hello {{ customer.first_name | default: "there" }}</p>
        {% if subscriber %}
            <p>Welcome back!</p>
        {% endif %}
        </body></html>
        """
        result = await check.run(html)
        assert result.passed is True
        assert result.score >= 0.8

    @pytest.mark.asyncio
    async def test_unmatched_if_endif(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        {% if customer %}
            <p>Hello!</p>
        </body></html>
        """
        result = await check.run(html)
        assert result.passed is False
        assert "Unclosed block" in (result.details or "")

    @pytest.mark.asyncio
    async def test_unclosed_for(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        {% for item in items %}
            <p>{{ item.name }}</p>
        </body></html>
        """
        result = await check.run(html)
        assert result.passed is False
        assert "Unclosed block" in (result.details or "")

    @pytest.mark.asyncio
    async def test_undefined_filter(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        <p>{{ name | super_custom_filter }}</p>
        </body></html>
        """
        result = await check.run(html)
        assert "unknown filter" in (result.details or "").lower()

    @pytest.mark.asyncio
    async def test_missing_default_filter(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        <p>{{ customer.address.city }}</p>
        </body></html>
        """
        result = await check.run(html)
        assert "default" in (result.details or "").lower()

    @pytest.mark.asyncio
    async def test_braze_passthrough(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        {% connected_content https://api.example.com :save response %}
        <p>{{ response.name }}</p>
        {{ content_blocks.${header_block} }}
        </body></html>
        """
        result = await check.run(html)
        # Braze templates should not flag connected_content as errors
        assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_excessive_nesting(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        {% if a %}{% if b %}{% if c %}{% if d %}{% if e %}{% if f %}
        Deep!
        {% endif %}{% endif %}{% endif %}{% endif %}{% endif %}{% endif %}
        </body></html>
        """
        result = await check.run(html)
        assert (
            "nesting" in (result.details or "").lower() or "depth" in (result.details or "").lower()
        )

    @pytest.mark.asyncio
    async def test_raw_block_preserved(self, check: LiquidSyntaxCheck) -> None:
        html = """
        <html><body>
        {% raw %}
        {% if this_is_literal %} not a real tag {% endif %}
        {% endraw %}
        </body></html>
        """
        result = await check.run(html)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_empty_html(self, check: LiquidSyntaxCheck) -> None:
        result = await check.run("")
        assert result.passed is True
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_config_disabled(self, check: LiquidSyntaxCheck) -> None:
        config = QACheckConfig(check_name="liquid_syntax", enabled=False)
        result = await check.run("{% if broken %}", config)
        assert result.passed is True
        assert "disabled" in (result.details or "").lower()
