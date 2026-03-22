"""Shared fixtures for email engine tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.knowledge.ontology.types import SupportLevel

# ── Real golden templates from the template library ──

LIBRARY_DIR = Path(__file__).resolve().parent.parent.parent / "ai" / "templates" / "library"


def load_golden_templates() -> dict[str, str]:
    """Load all golden template HTML files from the library directory."""
    templates: dict[str, str] = {}
    for html_file in sorted(LIBRARY_DIR.glob("*.html")):
        templates[html_file.stem] = html_file.read_text()
    return templates


# 5 representative templates covering different archetypes:
#   simple (minimal_text), complex multi-column (newsletter_2col),
#   dark-mode-heavy (promotional_hero), responsive (promotional_grid),
#   MSO-conditional-heavy (transactional_receipt)
REPRESENTATIVE_TEMPLATE_NAMES = [
    "minimal_text",
    "newsletter_2col",
    "promotional_hero",
    "promotional_grid",
    "transactional_receipt",
]


# ── Real component HTML from seeded components ──


def load_component_html() -> dict[str, str]:
    """Load component HTML from seed data.

    Returns dict keyed by slug: email-shell, email-header, email-footer,
    cta-button, hero-block, product-card, spacer, social-icons, etc.
    """
    from app.components.data.seeds import COMPONENT_SEEDS

    return {seed["slug"]: seed["html_source"] for seed in COMPONENT_SEEDS}


# Key components for CSS pipeline testing (7 of 21, covering all archetypes):
#   email-shell (full HTML doc wrapper — all CSS, dark mode, responsive, MSO),
#   hero-block (background images, overlay, complex layout),
#   cta-button (VML button with ghost variant),
#   column-layout-3 (multi-column with MSO table wrappers),
#   article-card (image + text + CTA composite),
#   image-grid (responsive grid layout),
#   navigation-bar (links with hover states)
REPRESENTATIVE_COMPONENT_SLUGS = [
    "email-shell",
    "hero-block",
    "cta-button",
    "column-layout-3",
    "article-card",
    "image-grid",
    "navigation-bar",
]


@pytest.fixture(scope="session")
def golden_templates() -> dict[str, str]:
    """All 15 golden template HTMLs keyed by name."""
    templates = load_golden_templates()
    assert len(templates) >= 5, f"Expected ≥5 golden templates, found {len(templates)}"
    return templates


@pytest.fixture(scope="session")
def representative_templates() -> dict[str, str]:
    """5 representative golden templates for equivalence/benchmark tests."""
    all_templates = load_golden_templates()
    result = {k: all_templates[k] for k in REPRESENTATIVE_TEMPLATE_NAMES if k in all_templates}
    assert len(result) >= 3, f"Expected ≥3 representative templates, found {len(result)}"
    return result


@pytest.fixture(scope="session")
def component_html() -> dict[str, str]:
    """All 21 seeded component HTMLs keyed by slug."""
    components = load_component_html()
    assert len(components) >= 5, f"Expected ≥5 component seeds, found {len(components)}"
    return components


@pytest.fixture(scope="session")
def representative_components() -> dict[str, str]:
    """7 representative component HTMLs for CSS pipeline tests."""
    all_components = load_component_html()
    result = {k: all_components[k] for k in REPRESENTATIVE_COMPONENT_SLUGS if k in all_components}
    assert len(result) >= 3, f"Expected ≥3 representative components, found {len(result)}"
    return result


# ── Mock ontology helpers ──


def make_mock_registry(
    *,
    support_none: bool = False,
    has_fallback: bool = False,
) -> MagicMock:
    """Create a mock OntologyRegistry for testing."""
    reg = MagicMock()
    prop = MagicMock()
    prop.id = "display_flex"
    prop.property_name = "display"
    prop.value = "flex"
    reg.find_property_by_name.return_value = prop

    if support_none:
        reg.get_support.return_value = SupportLevel.NONE
    else:
        reg.get_support.return_value = SupportLevel.FULL

    if has_fallback:
        fb = MagicMock()
        fb.target_property_id = "display_block"
        fb.client_ids = []
        fb.technique = "Use display:block as fallback"
        target_prop = MagicMock()
        target_prop.property_name = "display"
        target_prop.value = "block"
        reg.get_property.return_value = target_prop
        reg.fallbacks_for.return_value = [fb]
    else:
        reg.fallbacks_for.return_value = []

    return reg


@pytest.fixture
def mock_ontology_supported() -> Generator[MagicMock]:
    """Mock ontology where all properties are supported."""
    reg = make_mock_registry(support_none=False)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield reg


@pytest.fixture
def mock_ontology_unsupported() -> Generator[MagicMock]:
    """Mock ontology where all properties are unsupported (no fallback)."""
    reg = make_mock_registry(support_none=True, has_fallback=False)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield reg


@pytest.fixture
def mock_ontology_with_fallback() -> Generator[MagicMock]:
    """Mock ontology where properties are unsupported but have fallbacks."""
    reg = make_mock_registry(support_none=True, has_fallback=True)
    with (
        patch("app.email_engine.css_compiler.compiler.load_ontology", return_value=reg),
        patch("app.email_engine.css_compiler.conversions.load_ontology", return_value=reg),
    ):
        yield reg
