"""Custom QA check functions split into per-domain modules.

Importing this package triggers `register_custom_check` side effects for all
11 domain modules. The original 3,738-LOC `custom_checks.py` was split into
behaviour-preserving slices; see `.agents/plans/tech-debt-06-custom-checks-split.md`.

Each function follows the CustomCheckFn protocol:
    (doc, raw_html, config) -> (issues: list[str], deduction: float)
"""

from app.qa_engine.custom_checks import (
    a11y,
    brand,
    css,
    dark_mode,
    file_size,
    html,
    image,
    link,
    mso,
    personalisation,
    spam,
)

__all__ = [
    "a11y",
    "brand",
    "css",
    "dark_mode",
    "file_size",
    "html",
    "image",
    "link",
    "mso",
    "personalisation",
    "spam",
]
