"""Sandbox webmail profiles for DOM capture."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SandboxProfile:
    """A webmail interface to capture post-sanitizer DOM from."""

    name: str
    webmail_url_template: str  # Use {base_url} and {message_id} placeholders
    content_selector: str  # CSS selector for email body container
    login_required: bool = False
    wait_selector: str | None = None  # Extra selector to wait for before extraction
    browser: str = "cr"  # Playwright browser: "cr", "ff", "wk"


SANDBOX_PROFILES: dict[str, SandboxProfile] = {
    "mailpit": SandboxProfile(
        name="mailpit",
        webmail_url_template="{base_url}/view/{message_id}",
        content_selector=".message-body",
        browser="cr",
    ),
    "roundcube": SandboxProfile(
        name="roundcube",
        webmail_url_template="{base_url}/?_task=mail&_action=show&_uid={message_id}",
        content_selector="#messagebody",
        login_required=True,
        wait_selector="#messagebody .rcmBody",
        browser="cr",
    ),
}


def get_sandbox_profile(name: str) -> SandboxProfile | None:
    """Get a sandbox profile by name."""
    return SANDBOX_PROFILES.get(name)
