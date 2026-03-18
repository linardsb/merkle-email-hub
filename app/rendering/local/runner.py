"""Low-level Playwright CLI subprocess wrapper for screenshot capture."""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import ScreenshotRenderError, ScreenshotTimeoutError
from app.rendering.local.profiles import RenderingProfile

logger = get_logger(__name__)

STYLE_TAG_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)


def _prepare_html(html: str, profile: RenderingProfile) -> str:
    """Apply client-specific HTML modifications."""
    modified = html
    if profile.strip_style_tags:
        modified = STYLE_TAG_RE.sub("", modified)
    if profile.css_injections:
        injection = "<style>" + "\n".join(profile.css_injections) + "</style>"
        lower = modified.lower()
        if "</head>" in lower:
            idx = lower.index("</head>")
            modified = modified[:idx] + injection + modified[idx:]
        else:
            modified = injection + modified
    # Apply emulator transforms if profile has one
    if profile.emulator_id:
        from app.rendering.local.emulators import get_emulator

        emulator = get_emulator(profile.emulator_id)
        if emulator:
            modified = emulator.transform(modified)

    return modified


async def capture_screenshot(
    html: str,
    profile: RenderingProfile,
    output_dir: Path,
) -> bytes:
    """Render HTML with Playwright CLI and return PNG bytes."""
    settings = get_settings()
    timeout_ms = settings.rendering.screenshot_timeout_ms
    npx_path = settings.rendering.screenshot_npx_path

    prepared = _prepare_html(html, profile)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(prepared)
        html_path = f.name

    output_path = output_dir / f"{profile.name}.png"

    try:
        cmd = [npx_path, "playwright", "screenshot"]
        cmd.extend(["--browser", profile.browser])
        cmd.extend(["--viewport-size", f"{profile.viewport_width},{profile.viewport_height}"])
        cmd.append("--full-page")

        if profile.color_scheme == "dark":
            cmd.extend(["--color-scheme", "dark"])
        if profile.device:
            cmd.extend(["--device", profile.device])
        cmd.extend(["--wait-for-timeout", "1000"])

        cmd.append(f"file://{html_path}")
        cmd.append(str(output_path))

        logger.info(
            "screenshot.capture_started",
            profile=profile.name,
            browser=profile.browser,
            viewport=f"{profile.viewport_width}x{profile.viewport_height}",
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_ms / 1000)
        except TimeoutError as exc:
            proc.kill()
            raise ScreenshotTimeoutError(
                f"Screenshot for {profile.name} timed out after {timeout_ms}ms"
            ) from exc

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()[:500]
            raise ScreenshotRenderError(f"Playwright CLI failed for {profile.name}: {error_msg}")

        if not output_path.exists():
            raise ScreenshotRenderError(f"Screenshot file not created for {profile.name}")

        image_bytes = output_path.read_bytes()
        logger.info(
            "screenshot.capture_completed",
            profile=profile.name,
            size_bytes=len(image_bytes),
        )
        return image_bytes

    finally:
        try:
            Path(html_path).unlink()
        except OSError:
            pass
