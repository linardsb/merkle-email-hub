"""Decompression-bomb-safe wrapper around ``PIL.Image.open``."""

from __future__ import annotations

from pathlib import Path
from typing import IO

from PIL import Image

# ~64 MP — well under PIL default 89 MP, well above any legitimate email asset.
MAX_IMAGE_PIXELS = 64_000_000

ImageSource = str | Path | IO[bytes]


def safe_image_open(source: ImageSource) -> Image.Image:
    """Open an image with a tightened ``MAX_IMAGE_PIXELS`` guard.

    Pillow raises :class:`PIL.Image.DecompressionBombError` (during
    ``open`` or ``load``) when the pixel count exceeds the configured
    limit. Use this helper anywhere we accept image bytes/paths from
    user-controlled sources.
    """
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    return Image.open(source)
