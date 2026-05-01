"""Image edge color sampling for background color continuity."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

import numpy as np

from app.core.logging import get_logger
from app.shared.imaging import safe_image_open

logger = get_logger(__name__)


def sample_edge_color(
    image_path: Path,
    edge: Literal["top", "bottom"],
    *,
    strip_height: int = 4,
    tolerance: int = 10,
    min_uniformity: float = 0.80,
) -> str | None:
    """Sample the dominant color of an image edge strip.

    Reads a pixel strip from the top or bottom of the image, clusters
    pixels by RGB proximity (±tolerance per channel), and returns the
    hex color if the largest cluster covers ≥min_uniformity of pixels.

    Returns ``None`` for photographic/gradient edges or on any error.
    """
    path = Path(image_path)
    if not path.is_file():
        logger.warning("design_sync.edge_sample_missing_file", path=str(path))
        return None

    try:
        img = safe_image_open(path).convert("RGB")
    except Exception as exc:
        logger.warning(
            "design_sync.edge_sample_open_failed",
            path=str(path),
            error=str(exc),
        )
        return None

    w, h = img.size
    if h < strip_height or w == 0:
        return None

    # Extract strip
    if edge == "top":
        strip = img.crop((0, 0, w, strip_height))
    else:
        strip = img.crop((0, h - strip_height, w, h))

    pixels: np.ndarray = np.array(strip).reshape(-1, 3)  # (N, 3) uint8
    return _dominant_color(pixels, tolerance=tolerance, min_uniformity=min_uniformity)


def sample_centroid_color(
    image_bytes: bytes,
    *,
    cx: int,
    cy: int,
    block_size: int = 5,
    tolerance: int = 10,
    min_uniformity: float = 0.80,
) -> str | None:
    """Sample the dominant color of an NxN pixel block centred on ``(cx, cy)``.

    Used for detecting nested-card surfaces from a global design PNG when the
    section's own ``fills`` array is empty but the rendered design shows a
    distinct colour at the section's interior centroid (Phase 50.4, Gap 10).

    Returns ``None`` when the block falls outside the image, the image is
    unreadable, or the dominant cluster fails *min_uniformity*.
    """
    try:
        img = safe_image_open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        logger.warning("design_sync.centroid_sample_open_failed", error=str(exc))
        return None

    w, h = img.size
    if w == 0 or h == 0:
        return None

    half = max(1, block_size // 2)
    x0 = max(0, cx - half)
    y0 = max(0, cy - half)
    x1 = min(w, cx + half + 1)
    y1 = min(h, cy + half + 1)
    if x1 <= x0 or y1 <= y0:
        return None

    block = img.crop((x0, y0, x1, y1))
    pixels: np.ndarray = np.array(block).reshape(-1, 3)
    if len(pixels) == 0:
        return None
    return _dominant_color(pixels, tolerance=tolerance, min_uniformity=min_uniformity)


def _dominant_color(
    pixels: np.ndarray,
    *,
    tolerance: int,
    min_uniformity: float,
) -> str | None:
    """Find dominant color in pixel array via greedy clustering.

    Iterates pixels, assigns each to the first cluster whose centroid
    is within ±tolerance per RGB channel, or starts a new cluster.
    Returns hex of largest cluster if it meets *min_uniformity* threshold.
    """
    if len(pixels) == 0:
        return None

    # Greedy single-pass clustering
    clusters: list[tuple[np.ndarray, int]] = []  # (sum_rgb, count)

    for px in pixels:
        assigned = False
        for i, (rgb_sum, count) in enumerate(clusters):
            centroid = rgb_sum / count
            if np.all(np.abs(px.astype(np.int16) - centroid.astype(np.int16)) <= tolerance):
                clusters[i] = (rgb_sum + px.astype(np.int64), count + 1)
                assigned = True
                break
        if not assigned:
            clusters.append((px.astype(np.int64).copy(), 1))

    if not clusters:
        return None

    # Find largest cluster
    best_sum, best_count = max(clusters, key=lambda c: c[1])
    uniformity = best_count / len(pixels)

    if uniformity < min_uniformity:
        return None

    centroid = (best_sum / best_count).astype(np.uint8)
    r, g, b = int(centroid[0]), int(centroid[1]), int(centroid[2])
    hex_color = f"#{r:02X}{g:02X}{b:02X}"

    logger.info(
        "design_sync.edge_color_sampled",
        color=hex_color,
        uniformity=round(uniformity, 3),
        total_pixels=len(pixels),
    )
    return hex_color
