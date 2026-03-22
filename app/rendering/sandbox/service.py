"""Sandbox service — business logic with feature-flag gating."""

from __future__ import annotations

import base64

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rendering.exceptions import SandboxUnavailableError
from app.rendering.sandbox.sandbox import send_and_capture
from app.rendering.sandbox.schemas import (
    SandboxDOMDiff,
    SandboxHealthResponse,
    SandboxProfileResult,
    SandboxTestRequest,
    SandboxTestResponse,
)

logger = get_logger(__name__)


def _require_sandbox_enabled() -> None:
    """Raise if sandbox is disabled."""
    if not get_settings().rendering.sandbox.enabled:
        raise SandboxUnavailableError(
            "Email sandbox is disabled (RENDERING__SANDBOX__ENABLED=false)"
        )


async def run_sandbox_test(data: SandboxTestRequest) -> SandboxTestResponse:
    """Send email through sandbox and return capture results."""
    _require_sandbox_enabled()

    message_id, captures = await send_and_capture(
        html=data.html,
        subject=data.subject,
        profile_names=data.profiles,
    )

    results: list[SandboxProfileResult] = []
    for profile_name, rendered_html, screenshot, dom_diff in captures:
        screenshot_b64 = base64.b64encode(screenshot).decode() if screenshot else None
        diff_schema = None
        if dom_diff:
            diff_schema = SandboxDOMDiff(
                removed_elements=dom_diff.removed_elements,
                removed_attributes=dom_diff.removed_attributes,
                removed_css_properties=dom_diff.removed_css_properties,
                added_elements=dom_diff.added_elements,
                modified_styles=dom_diff.modified_styles,
            )
        results.append(
            SandboxProfileResult(
                profile=profile_name,
                rendered_html=rendered_html,
                screenshot_base64=screenshot_b64,
                dom_diff=diff_schema,
            )
        )

    return SandboxTestResponse(message_id=message_id, results=results)


async def check_sandbox_health() -> SandboxHealthResponse:
    """Check availability of sandbox infrastructure."""
    settings = get_settings()
    cfg = settings.rendering.sandbox

    if not cfg.enabled:
        return SandboxHealthResponse(sandbox_enabled=False)

    mailpit_ok = False
    roundcube_ok = False
    smtp_ok = False

    async with httpx.AsyncClient(timeout=5) as client:
        # Check Mailpit web UI
        try:
            resp = await client.get(f"{cfg.mailpit_url}/api/v1/messages")
            mailpit_ok = resp.status_code == 200
        except (httpx.HTTPError, OSError):
            pass

        # Check Roundcube
        try:
            resp = await client.get(cfg.roundcube_url)
            roundcube_ok = resp.status_code in (200, 302)  # 302 = redirect to login
        except (httpx.HTTPError, OSError):
            pass

    # Check SMTP connectivity
    try:
        import aiosmtplib

        smtp = aiosmtplib.SMTP(hostname=cfg.smtp_host, port=cfg.smtp_port)
        await smtp.connect()
        await smtp.quit()
        smtp_ok = True
    except Exception:
        logger.debug("sandbox.smtp_health_check_failed")

    return SandboxHealthResponse(
        sandbox_enabled=True,
        mailpit_reachable=mailpit_ok,
        roundcube_reachable=roundcube_ok,
        smtp_reachable=smtp_ok,
    )
