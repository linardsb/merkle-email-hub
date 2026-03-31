"""Unit tests for the file-based component loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.components.data.compatibility_presets import COMPAT_PRESETS, resolve_compatibility
from app.components.data.file_loader import _MANIFEST_PATH, _REPO_ROOT, load_file_components

_REQUIRED_SEED_KEYS = {
    "name",
    "slug",
    "description",
    "category",
    "html_source",
    "css_source",
    "compatibility",
    "slot_definitions",
    "default_tokens",
}


# ── Manifest loading ──


def test_manifest_loads_without_errors() -> None:
    """load_file_components() returns a non-empty list."""
    result = load_file_components()
    assert isinstance(result, list)
    assert len(result) > 0


def test_all_manifest_html_files_exist() -> None:
    """Every component in the manifest has a matching HTML file on disk."""
    import yaml

    with _MANIFEST_PATH.open() as f:
        data = yaml.safe_load(f)

    html_dir = _REPO_ROOT / data.get("html_dir", "email-templates/components")
    for entry in data["components"]:
        filename = entry.get("file", f"{entry['slug']}.html")
        html_path = html_dir / filename
        assert html_path.is_file(), f"Missing HTML for {entry['slug']}: {html_path}"


# ── Merged seed list ──


def test_no_duplicate_slugs_in_merged_seeds() -> None:
    """All slugs are unique across inline + file-based seeds."""
    from app.components.data.seeds import COMPONENT_SEEDS

    slugs = [s["slug"] for s in COMPONENT_SEEDS]
    assert len(slugs) == len(set(slugs)), (
        f"Duplicate slugs: {[s for s in slugs if slugs.count(s) > 1]}"
    )


def test_total_component_count() -> None:
    """Merged seed list contains inline shell + all file-based components."""
    from app.components.data.seeds import COMPONENT_SEEDS

    # 1 inline (email-shell) + 89 file-based = 90 total
    assert len(COMPONENT_SEEDS) == 90


# ── Seed dict shape ──


def test_file_seed_dict_shape() -> None:
    """Every file-based seed has all required keys with correct types."""
    seeds = load_file_components()
    for seed in seeds:
        missing = _REQUIRED_SEED_KEYS - set(seed)
        assert not missing, f"{seed['slug']} missing keys: {missing}"
        assert isinstance(seed["html_source"], str)
        assert len(seed["html_source"]) > 0, f"{seed['slug']} has empty html_source"
        assert isinstance(seed["slot_definitions"], list)
        assert isinstance(seed["compatibility"], dict)
        # Compatibility dict should have all 8 client keys
        assert len(seed["compatibility"]) == 8, (
            f"{seed['slug']} compat has {len(seed['compatibility'])} clients"
        )


# ── File-based source of truth ──


def test_email_shell_is_only_inline_seed() -> None:
    """Only email-shell remains as an inline seed; all others are file-based."""
    from app.components.data.seeds import _INLINE_SEEDS

    assert len(_INLINE_SEEDS) == 1
    assert _INLINE_SEEDS[0]["slug"] == "email-shell"


def test_all_converter_slugs_resolve() -> None:
    """Every slug emitted by the converter matcher resolves to a seed."""
    from app.components.data.seeds import COMPONENT_SEEDS

    seed_slugs = {s["slug"] for s in COMPONENT_SEEDS}
    converter_slugs = {
        "preheader",
        "logo-header",
        "email-header",
        "hero-block",
        "hero-text",
        "full-width-image",
        "cta-button",
        "email-footer",
        "social-icons",
        "divider",
        "spacer",
        "navigation-bar",
        "nav-hamburger",
        "editorial-2",
        "product-grid",
        "image-gallery",
        "image-grid",
        "article-card",
        "category-nav",
        "image-block",
        "text-block",
        "column-layout-2",
        "column-layout-3",
        "column-layout-4",
        "reverse-column",
        "product-card",
    }
    missing = converter_slugs - seed_slugs
    assert not missing, f"Converter slugs not found in seeds: {missing}"


# ── Missing file handling ──


def test_missing_html_file_skipped_with_warning(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Components with missing HTML files are skipped with a warning."""
    import yaml

    manifest = {
        "html_dir": str(tmp_path),
        "components": [
            {
                "slug": "nonexistent-component",
                "name": "Ghost",
                "description": "Does not exist.",
                "category": "utility",
                "compatibility": "full",
            },
        ],
    }

    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump(manifest))

    # Clear the lru_cache so our patched paths take effect
    from app.components.data.file_loader import _load_manifest

    _load_manifest.cache_clear()

    with (
        patch("app.components.data.file_loader._MANIFEST_PATH", manifest_path),
        patch("app.components.data.file_loader._REPO_ROOT", tmp_path),
    ):
        _load_manifest.cache_clear()
        result = load_file_components()

    # Restore cache for other tests
    _load_manifest.cache_clear()

    assert len(result) == 0
    captured = capsys.readouterr()
    assert "file_missing" in captured.out


# ── Compatibility preset resolution ──


def test_compatibility_preset_resolution() -> None:
    """String preset names resolve to full 8-client dicts."""
    result = resolve_compatibility("full")
    assert result == COMPAT_PRESETS["full"]
    assert len(result) == 8


def test_compatibility_unknown_preset_raises() -> None:
    """Unknown preset names raise ValueError."""
    with pytest.raises(ValueError, match="Unknown compatibility preset"):
        resolve_compatibility("nonexistent")


def test_compatibility_passthrough_dict() -> None:
    """Dict values pass through without resolution."""
    custom: dict[str, Any] = {"gmail": "full", "outlook_365": "partial"}
    result = resolve_compatibility(custom)
    assert result is custom


# ── Slot auto-detection ──


def test_extract_slots_from_html_finds_data_slots() -> None:
    """_extract_slots_from_html detects data-slot attributes."""
    from app.components.data.file_loader import _extract_slots_from_html

    html = '<td data-slot="heading">Hi</td><p data-slot="body">Text</p>'
    slots = _extract_slots_from_html(html)
    assert len(slots) == 2
    assert slots[0]["slot_id"] == "heading"
    assert slots[1]["slot_id"] == "body"
    assert slots[0]["selector"] == "[data-slot='heading']"


def test_extract_slots_deduplicates() -> None:
    """Repeated data-slot values produce a single entry."""
    from app.components.data.file_loader import _extract_slots_from_html

    html = '<td data-slot="x">A</td><td data-slot="x">B</td>'
    slots = _extract_slots_from_html(html)
    assert len(slots) == 1


def test_extract_slots_empty_html() -> None:
    """HTML with no data-slot attributes returns empty list."""
    from app.components.data.file_loader import _extract_slots_from_html

    slots = _extract_slots_from_html("<table><tr><td>No slots</td></tr></table>")
    assert slots == []


def test_manifest_fallback_to_auto_slots() -> None:
    """Components without manifest slot_definitions get auto-detected slots."""
    from app.components.data.seeds import COMPONENT_SEEDS

    # article-card has data-slot attrs in HTML but no explicit slot_definitions
    # was added to manifest — so auto-detect should find them.
    # Find a component that has data-slot in HTML to verify fallback works.
    text_block = next(s for s in COMPONENT_SEEDS if s["slug"] == "text-block")
    assert len(text_block["slot_definitions"]) >= 2  # heading + body
