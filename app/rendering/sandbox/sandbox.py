"""Email sandbox orchestrator — send, navigate, capture, diff."""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import SandboxCaptureError
from app.rendering.sandbox.dom_diff import DOMDiff, compute_dom_diff
from app.rendering.sandbox.profiles import SandboxProfile, get_sandbox_profile
from app.rendering.sandbox.smtp import send_test_email

logger = get_logger(__name__)


async def _wait_for_email_in_mailpit(message_id: str) -> str:
    """Poll Mailpit API until the message appears. Returns Mailpit internal ID."""
    import httpx

    settings = get_settings()
    base_url = settings.rendering.sandbox.mailpit_url
    timeout_ms = settings.rendering.sandbox.playwright_timeout_ms

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_ms / 1000
    async with httpx.AsyncClient() as client:
        while loop.time() < deadline:
            resp = await client.get(f"{base_url}/api/v1/messages", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for msg in data.get("messages", []):
                    if msg.get("MessageID") == message_id:
                        return str(msg["ID"])
            await asyncio.sleep(0.5)
    raise SandboxCaptureError(f"Email {message_id} not found in Mailpit within {timeout_ms}ms")


async def _capture_mailpit_html(mailpit_id: str) -> str:
    """Fetch rendered HTML directly from Mailpit API (no Playwright needed)."""
    import httpx

    settings = get_settings()
    base_url = settings.rendering.sandbox.mailpit_url

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/api/v1/message/{mailpit_id}/html", timeout=10)
        if resp.status_code != 200:
            raise SandboxCaptureError(f"Mailpit HTML fetch failed: HTTP {resp.status_code}")
        return resp.text


async def _capture_with_playwright(
    profile: SandboxProfile,
    mailpit_id: str,
) -> tuple[str, bytes | None]:
    """Open webmail in Playwright, extract DOM and optional screenshot.

    Returns (rendered_html, screenshot_bytes | None).
    """
    from playwright.async_api import async_playwright

    settings = get_settings()
    timeout = settings.rendering.sandbox.playwright_timeout_ms

    base_url_map = {
        "mailpit": settings.rendering.sandbox.mailpit_url,
        "roundcube": settings.rendering.sandbox.roundcube_url,
    }
    base_url = base_url_map.get(profile.name, settings.rendering.sandbox.mailpit_url)

    url = profile.webmail_url_template.format(
        base_url=base_url,
        message_id=mailpit_id,
    )

    async with async_playwright() as p:
        browser_launcher = {
            "cr": p.chromium,
            "ff": p.firefox,
            "wk": p.webkit,
        }.get(profile.browser, p.chromium)

        browser = await browser_launcher.launch(headless=True)
        try:
            page = await browser.new_page()
            page.set_default_timeout(timeout)

            await page.goto(url, wait_until="networkidle")

            if profile.wait_selector:
                await page.wait_for_selector(profile.wait_selector, timeout=timeout)
            else:
                await page.wait_for_selector(profile.content_selector, timeout=timeout)

            rendered_html: str = await page.eval_on_selector(
                profile.content_selector,
                "el => el.innerHTML",
            )

            # Capture screenshot (in-memory via Playwright API)
            screenshot: bytes | None = None
            try:
                element = await page.query_selector(profile.content_selector)
                if element:
                    screenshot = await element.screenshot(type="png")
                else:
                    screenshot = await page.screenshot(full_page=True, type="png")
            except Exception as exc:
                logger.warning("sandbox.screenshot_failed", profile=profile.name, error=str(exc))

            return rendered_html, screenshot
        finally:
            await browser.close()


async def send_and_capture(
    html: str,
    subject: str,
    profile_names: list[str],
) -> tuple[str, list[tuple[str, str, bytes | None, DOMDiff | None]]]:
    """Send email to sandbox and capture rendered DOM from each profile.

    Returns:
        (message_id, [(profile_name, rendered_html, screenshot, dom_diff), ...])
    """
    # Send email via SMTP
    message_id = await send_test_email(html, subject)

    # Wait for Mailpit to receive it
    mailpit_id = await _wait_for_email_in_mailpit(message_id)

    results: list[tuple[str, str, bytes | None, DOMDiff | None]] = []

    for name in profile_names:
        profile = get_sandbox_profile(name)
        if not profile:
            logger.warning("sandbox.unknown_profile", profile=name)
            continue

        try:
            if name == "mailpit":
                # Mailpit: use API directly (no sanitization — baseline)
                rendered = await _capture_mailpit_html(mailpit_id)
                screenshot: bytes | None = None
            else:
                # Webmail clients: use Playwright for real sanitizer capture
                rendered, screenshot = await _capture_with_playwright(profile, mailpit_id)

            dom_diff = compute_dom_diff(html, rendered)

            results.append((name, rendered, screenshot, dom_diff))

            logger.info(
                "sandbox.capture_completed",
                profile=name,
                removed_elements=len(dom_diff.removed_elements),
                removed_css=sum(len(v) for v in dom_diff.removed_css_properties.values()),
            )
        except Exception as exc:
            logger.error("sandbox.capture_failed", profile=name, error=str(exc))
            raise SandboxCaptureError(
                f"Sandbox capture failed for profile '{name}': {exc}"
            ) from exc

    return message_id, results
