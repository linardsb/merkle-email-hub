"""Shared email-client compatibility presets for component seeds."""

from typing import Any

COMPAT_PRESETS: dict[str, dict[str, str]] = {
    "full": {
        "gmail": "full",
        "outlook_365": "full",
        "outlook_2019": "full",
        "apple_mail": "full",
        "ios_mail": "full",
        "yahoo": "full",
        "samsung_mail": "full",
        "outlook_com": "full",
    },
    "partial_samsung": {
        "gmail": "full",
        "outlook_365": "full",
        "outlook_2019": "full",
        "apple_mail": "full",
        "ios_mail": "full",
        "yahoo": "full",
        "samsung_mail": "partial",
        "outlook_com": "full",
    },
    "partial_interactive": {
        "gmail": "none",
        "outlook_365": "none",
        "outlook_2019": "none",
        "apple_mail": "full",
        "ios_mail": "full",
        "yahoo": "none",
        "samsung_mail": "none",
        "outlook_com": "none",
    },
    "partial_animation": {
        "gmail": "none",
        "outlook_365": "none",
        "outlook_2019": "none",
        "apple_mail": "partial",
        "ios_mail": "partial",
        "yahoo": "none",
        "samsung_mail": "none",
        "outlook_com": "none",
    },
    "partial_outlook": {
        "gmail": "full",
        "outlook_365": "partial",
        "outlook_2019": "partial",
        "apple_mail": "full",
        "ios_mail": "full",
        "yahoo": "full",
        "samsung_mail": "full",
        "outlook_com": "partial",
    },
    "utility": {
        "gmail": "full",
        "outlook_365": "full",
        "outlook_2019": "full",
        "apple_mail": "full",
        "ios_mail": "full",
        "yahoo": "full",
        "samsung_mail": "full",
        "outlook_com": "full",
    },
}


def resolve_compatibility(value: str | dict[str, Any]) -> dict[str, str]:
    """Resolve a compatibility value to a full client dict.

    Accepts either a preset name (str) or a pre-built dict.
    """
    if isinstance(value, dict):
        return value
    if value not in COMPAT_PRESETS:
        msg = f"Unknown compatibility preset: {value!r}. Valid: {sorted(COMPAT_PRESETS)}"
        raise ValueError(msg)
    return dict(COMPAT_PRESETS[value])
