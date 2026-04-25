"""Tests for section-level screenshot cropping."""

from __future__ import annotations

import io

from PIL import Image

from app.rendering.screenshot_crop import crop_section
from app.shared.imaging import safe_image_open


def _make_solid_png(w: int, h: int, rgb: tuple[int, int, int] = (128, 128, 128)) -> bytes:
    img = Image.new("RGB", (w, h), rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _png_dimensions(data: bytes) -> tuple[int, int]:
    img = safe_image_open(io.BytesIO(data))
    return img.size  # (width, height)


class TestCropSection:
    def test_crop_section_basic(self) -> None:
        screenshot = _make_solid_png(680, 2000)
        result = crop_section(screenshot, y_offset=500, height=300, viewport_width=680)
        w, h = _png_dimensions(result)
        assert w == 680
        assert h == 300

    def test_crop_section_clamps_to_image_height(self) -> None:
        screenshot = _make_solid_png(680, 2000)
        result = crop_section(screenshot, y_offset=1900, height=300, viewport_width=680)
        w, h = _png_dimensions(result)
        assert w == 680
        assert h == 100  # clamped: 2000 - 1900

    def test_crop_section_small_height_returns_original(self) -> None:
        screenshot = _make_solid_png(680, 2000)
        result = crop_section(screenshot, y_offset=100, height=4, viewport_width=680)
        assert result == screenshot  # returned unchanged

    def test_crop_section_invalid_bytes_returns_original(self) -> None:
        bad_bytes = b"not-a-png"
        result = crop_section(bad_bytes, y_offset=0, height=100, viewport_width=680)
        assert result == bad_bytes  # graceful fallback
