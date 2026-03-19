"""Locale-specific email building: inject translations, apply RTL, compile via Maizzle."""

from __future__ import annotations

import asyncio
import html as html_mod
import re
import time

import httpx

from app.connectors.tolgee.exceptions import LocaleBuildError
from app.connectors.tolgee.schemas import LocaleBuildResult
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# RTL locales (BCP-47 primary subtags)
_RTL_LOCALES = frozenset({"ar", "he", "fa", "ur", "yi", "ps", "sd"})

# Gmail clipping threshold
_GMAIL_CLIP_BYTES = 102 * 1024


def _is_rtl(locale: str) -> bool:
    """Check if a locale uses right-to-left text direction."""
    primary = locale.split("-")[0].split("_")[0].lower()
    return primary in _RTL_LOCALES


def _apply_rtl(html_content: str, locale: str) -> str:
    """Apply RTL direction attributes for RTL locales."""
    if not _is_rtl(locale):
        return html_content

    # Add dir="rtl" to <html> tag
    html_content = re.sub(
        r"(<html\b)([^>]*)(>)",
        r'\1\2 dir="rtl"\3',
        html_content,
        count=1,
    )

    # Add dir="rtl" to <body> tag
    html_content = re.sub(
        r"(<body\b)([^>]*)(>)",
        r'\1\2 dir="rtl"\3',
        html_content,
        count=1,
    )

    return html_content


async def build_locale(
    template_html: str,
    translations: dict[str, str],
    locale: str,
    *,
    is_production: bool = False,
) -> LocaleBuildResult:
    """Build a single locale variant of an email template.

    Args:
        template_html: Source HTML with original (source) text
        translations: Mapping of source_text → translated_text
        locale: BCP-47 locale tag (e.g., "de", "ar", "ja")
        is_production: Whether to use production Maizzle build

    Returns:
        LocaleBuildResult with compiled HTML and metadata
    """
    start = time.monotonic()

    # Step 1: Replace source text with translations (text-safe injection)
    localized_html = template_html
    for source_text, translated_text in translations.items():
        if not translated_text:
            continue
        # HTML-escape the translated text to prevent injection on ALL paths
        safe_text = html_mod.escape(translated_text)
        # Replace escaped source text (appears in attributes, etc.)
        localized_html = localized_html.replace(html_mod.escape(source_text), safe_text)
        # Replace unescaped source text — still use escaped translation to prevent XSS
        localized_html = localized_html.replace(source_text, safe_text)

    # Step 2: Apply RTL direction if needed
    text_direction = "rtl" if _is_rtl(locale) else "ltr"
    localized_html = _apply_rtl(localized_html, locale)

    # Step 3: Add lang attribute to <html> tag
    localized_html = re.sub(
        r"(<html\b)([^>]*)(>)",
        rf'\1\2 lang="{locale}"\3',
        localized_html,
        count=1,
    )

    # Step 4: Build through Maizzle sidecar
    settings = get_settings()
    maizzle_url = settings.maizzle_builder_url
    payload = {
        "source": localized_html,
        "config": {"locale": locale},
        "production": is_production,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{maizzle_url}/build", json=payload)
            response.raise_for_status()
            data = response.json()
            compiled_html: str = data["html"]
    except httpx.HTTPError as exc:
        raise LocaleBuildError(f"Maizzle build failed for locale {locale}: {exc}") from exc

    # Step 5: Check Gmail clipping threshold
    html_bytes = len(compiled_html.encode("utf-8"))
    gmail_warning = html_bytes > _GMAIL_CLIP_BYTES

    if gmail_warning:
        logger.warning(
            "tolgee.gmail_clipping_risk",
            locale=locale,
            html_bytes=html_bytes,
            threshold=_GMAIL_CLIP_BYTES,
        )

    elapsed_ms = (time.monotonic() - start) * 1000

    return LocaleBuildResult(
        locale=locale,
        html=compiled_html,
        build_time_ms=round(elapsed_ms, 1),
        gmail_clipping_warning=gmail_warning,
        text_direction=text_direction,
    )


async def build_all_locales(
    template_html: str,
    locale_translations: dict[str, dict[str, str]],
    *,
    is_production: bool = False,
) -> list[LocaleBuildResult]:
    """Build template in multiple locales concurrently.

    Args:
        template_html: Source HTML template
        locale_translations: {locale: {source_text: translated_text}}
        is_production: Whether to use production Maizzle build

    Returns:
        List of LocaleBuildResult for each locale
    """
    tasks = [
        build_locale(template_html, translations, locale, is_production=is_production)
        for locale, translations in locale_translations.items()
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[LocaleBuildResult] = []
    for r in raw_results:
        if isinstance(r, BaseException):
            raise r
        results.append(r)
    return results
