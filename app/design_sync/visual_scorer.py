# pyright: reportUnknownVariableType=false, reportAssignmentType=false
"""SSIM-based visual fidelity scoring for Figma-to-HTML conversion.

Compares a Figma frame screenshot against the rendered HTML screenshot,
producing per-section fidelity scores and a visual diff overlay.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from app.core.logging import get_logger
from app.design_sync.figma.layout_analyzer import EmailSection

logger = get_logger(__name__)

# Minimum section height in pixels for SSIM to be meaningful
_MIN_SECTION_HEIGHT_PX = 8

# Luminance difference threshold for diff overlay (0-255 scale)
_DIFF_LUMINANCE_THRESHOLD = 51  # ~20% of 255


@dataclass(frozen=True)
class SectionScore:
    """Per-section SSIM fidelity score."""

    section_id: str
    section_name: str
    section_type: str
    ssim: float  # 0.0-1.0
    y_start: int  # pixel row in image
    y_end: int


@dataclass(frozen=True)
class FidelityScore:
    """Aggregate fidelity scoring result."""

    overall: float  # 0.0-1.0 (mean SSIM of all sections)
    sections: list[SectionScore]
    diff_image: bytes | None  # Red-highlighted diff overlay PNG


def _load_grayscale(image_bytes: bytes) -> np.ndarray:
    """Load PNG bytes as a float64 grayscale numpy array."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    return np.asarray(img, dtype=np.float64)


def _pad_to_match(img_a: np.ndarray, img_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pad images with white (255.0) so both have the same dimensions."""
    max_h = max(img_a.shape[0], img_b.shape[0])
    max_w = max(img_a.shape[1], img_b.shape[1])

    def _pad(img: np.ndarray) -> np.ndarray:
        if img.shape[0] == max_h and img.shape[1] == max_w:
            return img
        padded = np.full((max_h, max_w), 255.0, dtype=np.float64)
        padded[: img.shape[0], : img.shape[1]] = img
        return padded

    return _pad(img_a), _pad(img_b)


def _apply_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur to smooth anti-aliasing differences."""
    if sigma <= 0:
        return img
    from scipy.ndimage import gaussian_filter

    result: np.ndarray = gaussian_filter(img, sigma=sigma)
    return result


def _compute_ssim(img_a: np.ndarray, img_b: np.ndarray, *, win_size: int = 7) -> float:
    """Compute SSIM between two same-sized grayscale float64 arrays."""
    min_dim = min(img_a.shape[0], img_a.shape[1])
    effective_win = min(win_size, min_dim)
    # win_size must be odd
    if effective_win % 2 == 0:
        effective_win = max(effective_win - 1, 3)
    if effective_win < 3:
        return 1.0  # Image too small for meaningful SSIM

    score: float = structural_similarity(img_a, img_b, win_size=effective_win, data_range=255.0)
    return float(np.clip(score, 0.0, 1.0))


def _generate_diff_image(figma_gray: np.ndarray, html_gray: np.ndarray) -> bytes:
    """Generate a red-highlighted diff overlay PNG."""
    diff = np.abs(figma_gray - html_gray)

    # Create RGB image from figma reference as base
    _h, _w = figma_gray.shape
    rgb = np.stack([figma_gray] * 3, axis=-1).astype(np.uint8)

    # Highlight pixels exceeding luminance threshold in red
    mask = diff > _DIFF_LUMINANCE_THRESHOLD
    rgb[mask] = [255, 0, 0]

    img = Image.fromarray(rgb, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def score_fidelity(
    figma_image: bytes,
    html_image: bytes,
    sections: list[EmailSection],
    *,
    blur_sigma: float = 1.0,
    win_size: int = 7,
) -> FidelityScore:
    """Compare Figma frame image against rendered HTML screenshot.

    Args:
        figma_image: PNG bytes of the Figma frame export.
        html_image: PNG bytes of the rendered HTML screenshot.
        sections: Layout sections with y_position/height for per-section scoring.
        blur_sigma: Gaussian blur sigma to smooth anti-aliasing differences.
        win_size: SSIM Gaussian window size (must be odd, ≤ smallest image dim).

    Returns:
        FidelityScore with overall SSIM, per-section scores, and diff image.
    """
    figma_gray = _load_grayscale(figma_image)
    html_gray = _load_grayscale(html_image)

    # Pad to match dimensions
    figma_gray, html_gray = _pad_to_match(figma_gray, html_gray)

    # Apply blur to smooth anti-aliasing artifacts
    figma_blurred = _apply_blur(figma_gray, blur_sigma)
    html_blurred = _apply_blur(html_gray, blur_sigma)

    # Compute per-section scores
    section_scores: list[SectionScore] = []
    design_total_height = _compute_design_height(sections)

    if design_total_height > 0:
        img_height = figma_blurred.shape[0]
        scale = img_height / design_total_height

        for section in sections:
            if section.y_position is None or section.height is None:
                continue

            y_start = int(section.y_position * scale)
            y_end = int((section.y_position + section.height) * scale)
            y_end = min(y_end, img_height)

            if y_end - y_start < _MIN_SECTION_HEIGHT_PX:
                continue

            section_figma = figma_blurred[y_start:y_end, :]
            section_html = html_blurred[y_start:y_end, :]
            ssim_val = _compute_ssim(section_figma, section_html, win_size=win_size)

            section_scores.append(
                SectionScore(
                    section_id=section.node_id,
                    section_name=section.node_name,
                    section_type=section.section_type.value,
                    ssim=round(ssim_val, 4),
                    y_start=y_start,
                    y_end=y_end,
                )
            )

    # Overall score: mean of section SSIMs, or full-image SSIM if no sections
    if section_scores:
        overall = round(float(np.mean([s.ssim for s in section_scores])), 4)
    else:
        overall = _compute_ssim(figma_blurred, html_blurred, win_size=win_size)
        overall = round(overall, 4)

    # Generate diff image from unblurred originals for visual clarity
    diff_image = _generate_diff_image(figma_gray, html_gray)

    logger.info(
        "design_sync.fidelity_scored",
        overall_ssim=overall,
        section_count=len(section_scores),
        image_shape=figma_gray.shape,
    )

    return FidelityScore(
        overall=overall,
        sections=section_scores,
        diff_image=diff_image,
    )


def classify_severity(
    ssim: float,
    *,
    critical_threshold: float = 0.70,
    warning_threshold: float = 0.85,
) -> Literal["ok", "warning", "critical"]:
    """Classify SSIM score into severity level."""
    if ssim < critical_threshold:
        return "critical"
    if ssim < warning_threshold:
        return "warning"
    return "ok"


def _compute_design_height(sections: list[EmailSection]) -> float:
    """Compute total design height from section positions."""
    if not sections:
        return 0.0
    max_bottom = 0.0
    for s in sections:
        if s.y_position is not None and s.height is not None:
            bottom = s.y_position + s.height
            max_bottom = max(max_bottom, bottom)
    return max_bottom
