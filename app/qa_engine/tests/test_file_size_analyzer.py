"""Tests for app.qa_engine.file_size_analyzer module."""

import string
from collections.abc import Generator

import pytest

from app.qa_engine.file_size_analyzer import (
    analyze_file_size,
    clear_file_size_cache,
    get_cached_result,
)


@pytest.fixture(autouse=True)
def _clear_cache() -> Generator[None, None, None]:
    clear_file_size_cache()
    yield
    clear_file_size_cache()


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_html(body_content: str = "", extra_head: str = "") -> str:
    """Build minimal valid email HTML of controllable size."""
    return (
        '<!DOCTYPE html><html lang="en" xmlns:v="urn:schemas-microsoft-com:vml">'
        f'<head><meta charset="utf-8">{extra_head}</head>'
        f"<body>{body_content}</body></html>"
    )


def _make_padded_html(target_kb: float) -> str:
    """Create HTML of approximately target_kb size."""
    base = _make_html()
    base_bytes = len(base.encode("utf-8"))
    target_bytes = int(target_kb * 1024)
    padding_needed = max(0, target_bytes - base_bytes)
    # Use diverse content to get realistic gzip behavior
    padding = "Lorem ipsum " * (padding_needed // 12 + 1)
    return _make_html(body_content=padding[:padding_needed])


# ─── Test Classes ────────────────────────────────────────────────────────────


class TestBasicMeasurement:
    """Raw size and gzip measurement."""

    def test_small_html_size(self) -> None:
        html = _make_html("<p>Hello</p>")
        result = analyze_file_size(html)
        assert result.raw_size_bytes == len(html.encode("utf-8"))
        assert result.raw_size_kb < 1.0

    def test_gzip_smaller_than_raw(self) -> None:
        html = _make_padded_html(50)
        result = analyze_file_size(html)
        assert result.gzip_size_bytes < result.raw_size_bytes

    def test_compression_ratio_range(self) -> None:
        html = _make_padded_html(50)
        result = analyze_file_size(html)
        assert 0.0 < result.compression_ratio < 1.0

    def test_empty_html(self) -> None:
        result = analyze_file_size("")
        assert result.raw_size_bytes == 0
        assert result.gzip_size_bytes > 0  # gzip header overhead


class TestClientThresholds:
    """Threshold evaluation."""

    def test_under_all_thresholds(self) -> None:
        html = _make_padded_html(50)
        result = analyze_file_size(html)
        assert result.exceeded_clients == []

    def test_exceeds_yahoo_only(self) -> None:
        html = _make_padded_html(80)
        result = analyze_file_size(html)
        assert "yahoo" in result.exceeded_clients
        assert "gmail" not in result.exceeded_clients

    def test_exceeds_outlook_and_yahoo(self) -> None:
        html = _make_padded_html(101)
        result = analyze_file_size(html)
        assert "yahoo" in result.exceeded_clients
        assert "outlook" in result.exceeded_clients
        assert "braze" in result.exceeded_clients
        assert "gmail" not in result.exceeded_clients

    def test_exceeds_all_thresholds(self) -> None:
        html = _make_padded_html(105)
        result = analyze_file_size(html)
        assert len(result.exceeded_clients) == 4


class TestContentBreakdown:
    """Content category measurement."""

    def test_inline_styles_detected(self) -> None:
        html = _make_html('<div style="color: red; font-size: 16px; padding: 20px;">text</div>')
        result = analyze_file_size(html)
        assert result.breakdown.inline_styles_bytes > 0

    def test_head_styles_detected(self) -> None:
        html = _make_html(
            "<p>text</p>",
            extra_head="<style>body { color: red; } .cls { padding: 10px; }</style>",
        )
        result = analyze_file_size(html)
        assert result.breakdown.head_styles_bytes > 0

    def test_mso_conditionals_detected(self) -> None:
        html = _make_html("<!--[if mso]><table><tr><td>Outlook only</td></tr></table><![endif]-->")
        result = analyze_file_size(html)
        assert result.breakdown.mso_conditional_bytes > 0

    def test_image_tags_detected(self) -> None:
        html = _make_html(
            '<img src="https://example.com/image.jpg" alt="hero" width="600" height="400">'
        )
        result = analyze_file_size(html)
        assert result.breakdown.image_tag_bytes > 0

    def test_text_content_detected(self) -> None:
        html = _make_html("<p>This is some visible text content in the email body</p>")
        result = analyze_file_size(html)
        assert result.breakdown.text_content_bytes > 0

    def test_breakdown_sums_close_to_total(self) -> None:
        """All categories should sum close to total (within 10% tolerance)."""
        html = _make_html(
            '<div style="color:red"><p>text</p></div>',
            extra_head="<style>.x{color:blue}</style>",
        )
        result = analyze_file_size(html)
        b = result.breakdown
        cat_sum = (
            b.inline_styles_bytes
            + b.head_styles_bytes
            + b.mso_conditional_bytes
            + b.image_tag_bytes
            + b.html_structure_bytes
            + b.text_content_bytes
        )
        assert abs(cat_sum - b.total_bytes) / max(b.total_bytes, 1) < 0.10


class TestGzipEdgeCases:
    """Gzip compression edge cases."""

    def test_highly_repetitive_html(self) -> None:
        """Repetitive content should compress well."""
        html = _make_html("<p>repeat</p>" * 500)
        result = analyze_file_size(html)
        assert result.compression_ratio < 0.30  # >70% reduction

    def test_random_content_compresses_poorly(self) -> None:
        """Random/diverse content has higher compression ratio than repetitive."""
        import random

        rng = random.Random(42)
        chars = "".join(rng.choices(string.printable, k=50_000))
        html = _make_html(f"<p>{chars}</p>")
        result = analyze_file_size(html)
        # Random data compresses worse than repetitive data
        repetitive = _make_html("<p>repeat</p>" * 500)
        repetitive_result = analyze_file_size(repetitive)
        assert result.compression_ratio > repetitive_result.compression_ratio


class TestCaching:
    """Cache behavior."""

    def test_same_html_returns_cached(self) -> None:
        html = _make_html("<p>test</p>")
        r1 = get_cached_result(html)
        r2 = get_cached_result(html)
        assert r1 is r2  # Same object reference

    def test_clear_cache_recomputes(self) -> None:
        html = _make_html("<p>test</p>")
        r1 = get_cached_result(html)
        clear_file_size_cache()
        r2 = get_cached_result(html)
        assert r1 is not r2  # Different object
        assert r1.raw_size_bytes == r2.raw_size_bytes  # Same values
