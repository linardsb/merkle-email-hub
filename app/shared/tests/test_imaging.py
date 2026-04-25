"""Tests for the decompression-bomb-safe image opener."""

from __future__ import annotations

import io
import struct
import zlib

import pytest
from PIL import Image

from app.shared.imaging import MAX_IMAGE_PIXELS, safe_image_open


def _make_png_header_only(width: int, height: int) -> bytes:
    """Build a minimal PNG (signature + IHDR + IDAT + IEND) for the given dims.

    The IDAT chunk holds a single compressed zero-length filter row; Pillow
    reads dimensions from IHDR during ``open``, which is enough to trigger
    the ``MAX_IMAGE_PIXELS`` check without allocating a real bitmap.
    """
    signature = b"\x89PNG\r\n\x1a\n"

    def _chunk(tag: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return length + tag + data + crc

    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,  # bit depth
        0,  # colour type: grayscale
        0,
        0,
        0,
    )
    idat = zlib.compress(b"\x00")  # one filter byte; not a real scanline
    return signature + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def test_safe_image_open_rejects_bomb() -> None:
    """An image with more pixels than 2 * MAX_IMAGE_PIXELS must raise."""
    # Pillow only escalates from warning to ``DecompressionBombError`` when
    # the pixel count exceeds 2 * MAX_IMAGE_PIXELS — pick a size well above
    # that threshold.
    side = 16_000  # 2.56e8 pixels > 2 * 6.4e7
    assert side * side > 2 * MAX_IMAGE_PIXELS

    bomb = _make_png_header_only(side, side)

    with pytest.raises(Image.DecompressionBombError):
        img = safe_image_open(io.BytesIO(bomb))
        # Pillow may defer the bomb check to ``.load()`` depending on
        # version/format — force it.
        img.load()


def test_safe_image_open_allows_normal_image() -> None:
    """A small image must pass through unchanged."""
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (255, 0, 0)).save(buf, format="PNG")
    buf.seek(0)

    with safe_image_open(buf) as img:
        assert img.size == (16, 16)
