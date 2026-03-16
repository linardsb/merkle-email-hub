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
    css_injections: list[str] = field(default_factory=lambda: [])
    strip_style_tags: bool = False
    max_screenshot_height: int = 4096


CLIENT_PROFILES: dict[str, RenderingProfile] = {
    "gmail_web": RenderingProfile(
        name="gmail_web",
        viewport_width=680,
        viewport_height=900,
        browser="cr",
        strip_style_tags=True,
        css_injections=["body { max-width: 680px; margin: 0 auto; }"],
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
}
