"""Visual diff service using ODiff for perceptual image comparison."""

from __future__ import annotations

import asyncio
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import VisualDiffError

logger = get_logger(__name__)

# ODiff outputs: "Files are different. NN changed pixels (X.XX% of all)"
DIFF_PERCENTAGE_RE = re.compile(r"([\d.]+)%")
PIXEL_COUNT_RE = re.compile(r"(\d+)\s+changed\s+pixels")


@dataclass(frozen=True)
class DiffResult:
    """Result of an ODiff comparison."""

    identical: bool
    diff_percentage: float
    diff_image: bytes | None  # PNG bytes of diff overlay, None if identical
    pixel_count: int
    changed_regions: list[tuple[int, int, int, int]]  # (x, y, w, h) tuples


async def run_odiff(
    baseline_path: Path,
    current_path: Path,
    output_path: Path,
    *,
    threshold: float = 0.01,
) -> DiffResult:
    """Run ODiff binary comparison between two images.

    ODiff exit codes:
    - 0: images identical
    - 1: images different (diff written to output_path)
    - 2: error (dimension mismatch, corrupt images, etc.)
    """
    cmd = [
        "npx",
        "odiff",
        str(baseline_path),
        str(current_path),
        str(output_path),
        "--threshold",
        str(threshold),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    except TimeoutError as exc:
        raise VisualDiffError("ODiff comparison timed out after 30s") from exc
    except FileNotFoundError as exc:
        raise VisualDiffError(
            "ODiff binary not found — install via: npm install odiff-bin"
        ) from exc

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode == 0:
        return DiffResult(
            identical=True,
            diff_percentage=0.0,
            diff_image=None,
            pixel_count=0,
            changed_regions=[],
        )

    if proc.returncode == 2:
        error_msg = (stderr_text or stdout_text)[:500]
        raise VisualDiffError(f"ODiff comparison error: {error_msg}")

    # returncode == 1 — images differ
    diff_percentage = 0.0
    pixel_count = 0

    pct_match = DIFF_PERCENTAGE_RE.search(stdout_text)
    if pct_match:
        diff_percentage = float(pct_match.group(1))

    px_match = PIXEL_COUNT_RE.search(stdout_text)
    if px_match:
        pixel_count = int(px_match.group(1))

    diff_image: bytes | None = None
    if output_path.exists():
        diff_image = output_path.read_bytes()

    logger.info(
        "visual_diff.compared",
        diff_percentage=diff_percentage,
        pixel_count=pixel_count,
        identical=False,
    )

    return DiffResult(
        identical=False,
        diff_percentage=diff_percentage,
        diff_image=diff_image,
        pixel_count=pixel_count,
        changed_regions=[],  # ODiff doesn't output bounding boxes natively
    )


async def compare_images(
    baseline_bytes: bytes,
    current_bytes: bytes,
    *,
    threshold: float | None = None,
) -> DiffResult:
    """Compare two PNG images using ODiff. High-level entry point."""
    settings = get_settings()
    effective_threshold = (
        threshold if threshold is not None else settings.rendering.visual_diff_threshold
    )

    with tempfile.TemporaryDirectory(prefix="odiff_") as tmpdir:
        tmp = Path(tmpdir)
        baseline_path = tmp / "baseline.png"
        current_path = tmp / "current.png"
        output_path = tmp / "diff.png"

        baseline_path.write_bytes(baseline_bytes)
        current_path.write_bytes(current_bytes)

        return await run_odiff(
            baseline_path, current_path, output_path, threshold=effective_threshold
        )
