"""Section-level screenshot cropping utility."""

from __future__ import annotations

import io

from PIL import Image

from app.core.logging import get_logger

logger = get_logger(__name__)

_MIN_SECTION_HEIGHT_PX = 8


def crop_section(
    full_screenshot: bytes,
    y_offset: int,
    height: int,
    viewport_width: int,
) -> bytes:
    """Crop a full-page screenshot to a single section's bounds.

    Args:
        full_screenshot: Full-page PNG bytes (from Playwright).
        y_offset: Top edge of the section in pixels.
        height: Section height in pixels.
        viewport_width: Expected image width in pixels.

    Returns:
        Cropped PNG bytes. Falls back to full screenshot on error.
    """
    if height < _MIN_SECTION_HEIGHT_PX:
        logger.warning(
            "rendering.crop_skipped_small",
            y_offset=y_offset,
            height=height,
            min_height=_MIN_SECTION_HEIGHT_PX,
        )
        return full_screenshot

    try:
        img = Image.open(io.BytesIO(full_screenshot))
        img_width, img_height = img.size

        # Clamp bottom edge to image bounds
        y_end = min(y_offset + height, img_height)
        if y_end <= y_offset:
            logger.warning(
                "rendering.crop_out_of_bounds",
                y_offset=y_offset,
                height=height,
                img_height=img_height,
            )
            return full_screenshot

        cropped = img.crop((0, y_offset, min(viewport_width, img_width), y_end))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        logger.info(
            "rendering.section_cropped",
            y_offset=y_offset,
            height=height,
            cropped_height=y_end - y_offset,
        )
        return buf.getvalue()
    except Exception as exc:
        logger.warning("rendering.crop_failed", error=str(exc))
        return full_screenshot
