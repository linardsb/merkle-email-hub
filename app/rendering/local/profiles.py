"""Email client simulation profiles for Playwright CLI rendering."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RenderingProfile:
    """Email client simulation profile for Playwright CLI."""

    name: str
    viewport_width: int
    viewport_height: int
    browser: str  # "cr" (chromium), "wk" (webkit), "ff" (firefox)
    color_scheme: str = "light"
    device: str | None = None
    css_injections: list[str] = field(default_factory=list)
    strip_style_tags: bool = False
    max_screenshot_height: int = 4096
    emulator_id: str | None = None


CLIENT_PROFILES: dict[str, RenderingProfile] = {
    "gmail_web": RenderingProfile(
        name="gmail_web",
        viewport_width=680,
        viewport_height=900,
        browser="cr",
        strip_style_tags=True,
        css_injections=["body { max-width: 680px; margin: 0 auto; }"],
        emulator_id="gmail_web",
    ),
    "outlook_2019": RenderingProfile(
        name="outlook_2019",
        viewport_width=800,
        viewport_height=900,
        browser="cr",
        css_injections=[
            "* { display: block !important; }",
            "body { max-width: 800px; }",
            "[style*='display:flex'], [style*='display: flex'] { display: block !important; }",
            "[style*='display:grid'], [style*='display: grid'] { display: block !important; }",
        ],
    ),
    "apple_mail": RenderingProfile(
        name="apple_mail",
        viewport_width=600,
        viewport_height=900,
        browser="wk",
    ),
    "outlook_dark": RenderingProfile(
        name="outlook_dark",
        viewport_width=800,
        viewport_height=900,
        browser="cr",
        color_scheme="dark",
        css_injections=[
            "body { background-color: #1e1e1e; color: #ffffff; }",
            "* { display: block !important; }",
        ],
    ),
    "mobile_ios": RenderingProfile(
        name="mobile_ios",
        viewport_width=375,
        viewport_height=812,
        browser="wk",
        device="iPhone 13",
    ),
    "outlook_web": RenderingProfile(
        name="outlook_web",
        viewport_width=680,
        viewport_height=900,
        browser="cr",
        emulator_id="outlook_web",
    ),
    # ── Yahoo ──
    "yahoo_web": RenderingProfile(
        name="yahoo_web",
        viewport_width=800,
        viewport_height=900,
        browser="cr",
        emulator_id="yahoo_web",
    ),
    "yahoo_mobile": RenderingProfile(
        name="yahoo_mobile",
        viewport_width=375,
        viewport_height=812,
        browser="wk",
        device="iPhone 13",
        emulator_id="yahoo_mobile",
    ),
    # ── Samsung ──
    "samsung_mail": RenderingProfile(
        name="samsung_mail",
        viewport_width=360,
        viewport_height=780,
        browser="cr",
        emulator_id="samsung_mail",
    ),
    "samsung_mail_dark": RenderingProfile(
        name="samsung_mail_dark",
        viewport_width=360,
        viewport_height=780,
        browser="cr",
        color_scheme="dark",
        emulator_id="samsung_mail",
    ),
    # ── Outlook Desktop (Word engine — CSS preprocessing only) ──
    "outlook_desktop": RenderingProfile(
        name="outlook_desktop",
        viewport_width=800,
        viewport_height=900,
        browser="cr",
        emulator_id="outlook_desktop",
    ),
    # ── Thunderbird (Gecko) ──
    "thunderbird": RenderingProfile(
        name="thunderbird",
        viewport_width=700,
        viewport_height=900,
        browser="ff",
        emulator_id="thunderbird",
    ),
    # ── Android Gmail ──
    "android_gmail": RenderingProfile(
        name="android_gmail",
        viewport_width=360,
        viewport_height=780,
        browser="cr",
        emulator_id="android_gmail",
    ),
    "android_gmail_dark": RenderingProfile(
        name="android_gmail_dark",
        viewport_width=360,
        viewport_height=780,
        browser="cr",
        color_scheme="dark",
        emulator_id="android_gmail",
    ),
}
