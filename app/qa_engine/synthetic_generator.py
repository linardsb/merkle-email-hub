"""Synthetic adversarial email generator.

Produces emails with known defects for QA check false-negative testing.
Each injector targets a specific QA check, creating realistic mutations
that a human reviewer would catch but automated checks might miss.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)

_PAD_CHAR = "A"

# Checks that have targeted injectors (11 of 14; skip css_audit, deliverability, css_support)
TARGET_CHECKS: tuple[str, ...] = (
    "html_validation",
    "accessibility",
    "link_validation",
    "dark_mode",
    "image_optimization",
    "liquid_syntax",
    "personalisation_syntax",
    "spam_score",
    "brand_compliance",
    "fallback",
    "file_size",
)

_DIFFICULTY_CYCLE: tuple[Literal["easy", "medium", "hard"], ...] = (
    "easy",
    "easy",
    "medium",
    "medium",
    "hard",
)


@dataclass(frozen=True)
class SyntheticEmail:
    """A generated email with a known defect."""

    id: str
    html: str
    expected_failures: dict[str, bool]
    defect_category: str
    defect_description: str
    difficulty: Literal["easy", "medium", "hard"]
    base_template: str


@dataclass(frozen=True)
class SyntheticManifest:
    """Metadata-only manifest for a generated set."""

    generated_at: str
    count: int
    emails: list[dict[str, object]]


def load_base_templates() -> dict[str, str]:
    """Load golden templates from library directory."""
    library = Path(__file__).resolve().parent.parent / "ai" / "templates" / "library"
    templates: dict[str, str] = {}
    for html_file in sorted(library.glob("*.html")):
        templates[html_file.stem] = html_file.read_text()
    return templates


# ---------------------------------------------------------------------------
# Defect injectors
# ---------------------------------------------------------------------------


def _inject_html_validation(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        return html.replace("<!DOCTYPE html>", "", 1), "Removed <!DOCTYPE html> declaration"
    if difficulty == "medium":
        # Remove first closing </td> to create an unclosed tag
        return html.replace("</td>", "", 1), "Removed first </td> closing tag"
    # hard
    result = re.sub(r"<meta\s+charset=[^>]*>", "", html, count=1)
    result = re.sub(r"<title>[^<]*</title>", "", result, count=1)
    return result, "Removed <meta charset> and <title>"


def _inject_accessibility(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        # Remove alt attributes from img tags
        result = re.sub(r'\s+alt="[^"]*"', "", html)
        return result, "Removed all alt attributes from images"
    if difficulty == "medium":
        # Set low contrast color on a td
        result = html.replace("color:", "color: #777777; original-color:", 1)
        return result, "Injected low-contrast #777777 text color"
    # hard: remove role="presentation" and lang attribute
    result = re.sub(r'\s+role="presentation"', "", html)
    result = re.sub(r'\s+lang="[^"]*"', "", result, count=1)
    return result, "Removed role='presentation' and lang attribute"


def _inject_link_validation(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        return re.sub(
            r'<a\s+href="[^"]*"',
            '<a href="javascript:void(0)"',
            html,
            count=1,
        ), "Injected javascript: protocol in first link"
    if difficulty == "medium":
        return re.sub(
            r'href="https://',
            'href="http://',
            html,
            count=1,
        ), "Downgraded first HTTPS link to HTTP"
    # hard: mailto with header injection
    return re.sub(
        r'<a\s+href="[^"]*"',
        '<a href="mailto:test@example.com%0ACc:attacker@evil.com"',
        html,
        count=1,
    ), "Injected mailto with header injection"


def _inject_dark_mode(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        result = re.sub(
            r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{[^}]*\}",
            "",
            html,
            count=1,
        )
        return result, "Removed @media (prefers-color-scheme: dark) block"
    if difficulty == "medium":
        # Hardcode black color without dark mode override
        return html.replace(
            "</style>",
            ".force-black { color: #000000 !important; }</style>",
            1,
        ), "Added hardcoded #000000 color without dark mode override"
    # hard: remove color-scheme meta + all dark mode
    result = re.sub(r'<meta\s+name="color-scheme"[^>]*>', "", html)
    result = re.sub(r'<meta\s+name="supported-color-schemes"[^>]*>', "", result)
    result = re.sub(
        r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{[^}]*\}",
        "",
        result,
    )
    result = re.sub(r"\[data-ogsc\][^\n]*\n", "", result)
    result = re.sub(r"\[data-ogsb\][^\n]*\n", "", result)
    return result, "Removed all dark mode support (meta, media queries, Outlook overrides)"


def _inject_image_optimization(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        # Remove width/height from images
        result = re.sub(r'\s+width="\d+"', "", html)
        result = re.sub(r'\s+height="\d+"', "", result)
        return result, "Removed width/height attributes from images"
    if difficulty == "medium":
        return re.sub(
            r'width="\d+"',
            'width="2000"',
            html,
            count=1,
        ), "Set oversized width=2000 on first image"
    # hard: non-retina dimension mismatch
    return re.sub(
        r'<img([^>]*?)width="\d+"',
        '<img\\1width="600" data-src-width="1200"',
        html,
        count=1,
    ), "Added non-retina dimension mismatch (600px display for 1200px source)"


def _inject_liquid_syntax(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        # Insert unclosed {% if %} block
        insertion = '{% if subscriber.vip %}<td style="font-family: Arial; font-size: 14px; color: #333;">VIP Content</td>'
        return html.replace(
            "</table>", f"{insertion}</table>", 1
        ), "Injected unclosed {% if %} without {% endif %}"
    if difficulty == "medium":
        insertion = '{% if {{ user.name }} == "test" %}matched{% endif %}'
        return html.replace(
            "</td>", f"{insertion}</td>", 1
        ), "Injected nested {{ }} inside {% %} block"
    # hard: mixed Braze + SFMC syntax
    insertion = "{{user.first_name}} %%=v(@first_name)=%%"
    return html.replace(
        "</td>", f"{insertion}</td>", 1
    ), "Injected mixed Braze and SFMC personalisation syntax"


def _inject_personalisation(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        return re.sub(
            r'href="[^"]*"',
            'href="https://example.com?name=%%first_name%%"',
            html,
            count=1,
        ), "Injected unescaped %%first_name%% in href"
    if difficulty == "medium":
        return html.replace(
            "<title>",
            "<title>%%=v(@subject_line)=%% ",
            1,
        ), "Injected AMPscript in subject/title"
    # hard: unclosed personalisation block
    return html.replace(
        "</td>",
        '%%[ SET @name = "test" </td>',
        1,
    ), "Injected unclosed %%[ AMPscript block"


def _inject_spam_score(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        result = re.sub(
            r"<title>[^<]*</title>",
            "<title>FREE!!! ACT NOW!!!</title>",
            html,
            count=1,
        )
        return result, "ALL CAPS spam trigger words in subject/title"
    if difficulty == "medium":
        hidden = '<td style="font-size: 0; line-height: 0; color: #ffffff;">Buy now free discount limited offer</td>'
        return html.replace(
            "</tr>", f"<tr>{hidden}</tr></tr>", 1
        ), "Injected font-size:0 hidden spam text"
    # hard: multiple triggers
    result = re.sub(
        r"<title>[^<]*</title>",
        "<title>URGENT!!! FREE MONEY!!! ACT NOW!!!</title>",
        html,
        count=1,
    )
    spam_content = '<td style="font-family: Arial; font-size: 16px; color: #ff0000;">CLICK HERE NOW!!! 100% FREE!!! LIMITED TIME OFFER!!!</td>'
    result = result.replace("</tr>", f"<tr>{spam_content}</tr></tr>", 1)
    return result, "Multiple spam triggers: ALL CAPS subject + red text + exclamation overuse"


def _inject_brand_compliance(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        # Inject off-brand red color
        return re.sub(
            r"color:\s*#[0-9a-fA-F]{6}",
            "color: #FF0000",
            html,
            count=1,
        ), "Replaced first color with off-brand #FF0000"
    if difficulty == "medium":
        return re.sub(
            r"font-family:[^;]+;",
            "font-family: 'Comic Sans MS', cursive;",
            html,
            count=1,
        ), "Replaced first font-family with Comic Sans"
    # hard: off-brand color + wrong font + remove logo
    result = re.sub(r"color:\s*#[0-9a-fA-F]{6}", "color: #FF0000", result := html, count=2)
    result = re.sub(
        r"font-family:[^;]+;",
        "font-family: 'Comic Sans MS', cursive;",
        result,
        count=2,
    )
    result = re.sub(r"<img[^>]*logo[^>]*/?>", "", result, flags=re.IGNORECASE)
    return result, "Off-brand colors + Comic Sans + removed logo image"


def _inject_fallback(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    if difficulty == "easy":
        # Remove one MSO conditional block
        return re.sub(
            r"<!--\[if mso\]>.*?<!\[endif\]-->",
            "",
            html,
            count=1,
            flags=re.DOTALL,
        ), "Removed first <!--[if mso]> conditional block"
    if difficulty == "medium":
        # Remove VML namespace
        result = re.sub(r'\s+xmlns:v="[^"]*"', "", html)
        result = re.sub(r'\s+xmlns:o="[^"]*"', "", result)
        return result, "Removed VML/Office namespace declarations"
    # hard: remove all MSO conditionals
    result = re.sub(
        r"<!--\[if mso\]>.*?<!\[endif\]-->",
        "",
        html,
        flags=re.DOTALL,
    )
    return result, "Removed ALL MSO conditional blocks"


def _inject_file_size(html: str, difficulty: str, _idx: int) -> tuple[str, str]:
    target_kb = {
        "easy": 101,
        "medium": 102,
        "hard": 103,
    }
    target_bytes = target_kb.get(difficulty, 101) * 1024
    current_bytes = len(html.encode("utf-8"))
    if current_bytes >= target_bytes:
        return html, f"Already exceeds {target_kb.get(difficulty, 101)}KB"
    pad_needed = target_bytes - current_bytes
    # Insert a hidden base64-like data block as an HTML comment before </body>
    padding = f"<!-- {_PAD_CHAR * pad_needed} -->"
    result = html.replace("</body>", f"{padding}</body>", 1)
    return result, f"Padded to {target_kb.get(difficulty, 101)}KB to trigger file size check"


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

_InjectorFn = Callable[[str, str, int], tuple[str, str]]

_INJECTORS: dict[str, _InjectorFn] = {
    "html_validation": _inject_html_validation,
    "accessibility": _inject_accessibility,
    "link_validation": _inject_link_validation,
    "dark_mode": _inject_dark_mode,
    "image_optimization": _inject_image_optimization,
    "liquid_syntax": _inject_liquid_syntax,
    "personalisation_syntax": _inject_personalisation,
    "spam_score": _inject_spam_score,
    "brand_compliance": _inject_brand_compliance,
    "fallback": _inject_fallback,
    "file_size": _inject_file_size,
}


class SyntheticEmailGenerator:
    """Generates adversarial emails with targeted defects."""

    def __init__(self, base_templates: dict[str, str] | None = None) -> None:
        self._templates = base_templates or load_base_templates()
        self._template_names = sorted(self._templates.keys())
        self._injectors: dict[str, _InjectorFn] = dict(_INJECTORS)

    def generate_for_check(self, check_name: str, count: int = 5) -> list[SyntheticEmail]:
        """Generate adversarial emails targeting a specific QA check."""
        if check_name not in self._injectors:
            msg = f"No injector for check: {check_name}"
            raise ValueError(msg)

        injector = self._injectors[check_name]
        emails: list[SyntheticEmail] = []

        for idx in range(count):
            template_name = self._template_names[idx % len(self._template_names)]
            template_html = self._templates[template_name]
            difficulty = _DIFFICULTY_CYCLE[idx % len(_DIFFICULTY_CYCLE)]

            mutated_html, description = injector(template_html, difficulty, idx)

            email = SyntheticEmail(
                id=f"{check_name}_{idx:03d}",
                html=mutated_html,
                expected_failures={check_name: True},
                defect_category=check_name,
                defect_description=description,
                difficulty=difficulty,
                base_template=template_name,
            )
            emails.append(email)

        return emails

    def generate_adversarial_set(self, count_per_check: int = 5) -> list[SyntheticEmail]:
        """Generate adversarial emails for all target checks."""
        all_emails: list[SyntheticEmail] = []
        for check_name in TARGET_CHECKS:
            all_emails.extend(self.generate_for_check(check_name, count_per_check))

        logger.info(
            "synthetic.generation_completed",
            total=len(all_emails),
            checks=len(TARGET_CHECKS),
            count_per_check=count_per_check,
        )
        return all_emails

    @staticmethod
    def save(emails: list[SyntheticEmail], output_dir: Path) -> Path:
        """Save generated emails and manifest to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)

        for email in emails:
            (output_dir / f"{email.id}.html").write_text(email.html, encoding="utf-8")

        manifest_entries: list[dict[str, object]] = []
        for email in emails:
            entry: dict[str, object] = asdict(email)
            del entry["html"]
            manifest_entries.append(entry)

        manifest = SyntheticManifest(
            generated_at=datetime.now(tz=UTC).isoformat(),
            count=len(emails),
            emails=manifest_entries,
        )
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(asdict(manifest), indent=2),
            encoding="utf-8",
        )

        logger.info(
            "synthetic.save_completed",
            output_dir=str(output_dir),
            count=len(emails),
        )
        return output_dir
