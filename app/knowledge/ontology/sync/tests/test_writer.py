"""Tests for YAML writer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

from app.knowledge.ontology.sync.schemas import CanIEmailFeature, SyncDiff
from app.knowledge.ontology.sync.writer import apply_sync


def _make_feature(
    slug: str = "css-display-flex",
    title: str = "display:flex",
) -> CanIEmailFeature:
    return CanIEmailFeature(
        slug=slug,
        title=title,
        category="css",
        last_test_date="2024-01-01",
        stats={},
        notes={},
    )


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


class TestApplySync:
    def test_returns_zero_when_no_changes(self) -> None:
        diff = SyncDiff()
        result = apply_sync([], diff)
        assert result == 0

    def test_appends_new_properties(self, tmp_path: Path) -> None:
        props_path = tmp_path / "css_properties.yaml"
        support_path = tmp_path / "support_matrix.yaml"
        _write_yaml(props_path, {"properties": []})
        _write_yaml(support_path, {"support": []})

        diff = SyncDiff(new_properties=["display_flex"])
        feat = _make_feature()

        with (
            patch("app.knowledge.ontology.sync.writer._DATA_DIR", tmp_path),
            patch("app.knowledge.ontology.sync.writer.load_ontology") as mock_load,
        ):
            result = apply_sync([feat], diff)
            mock_load.cache_clear.assert_called_once()

        assert result == 1

        with props_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["properties"]) == 1
        assert data["properties"][0]["id"] == "display_flex"
        assert data["properties"][0]["property_name"] == "display"

    def test_updates_existing_support_level(self, tmp_path: Path) -> None:
        props_path = tmp_path / "css_properties.yaml"
        support_path = tmp_path / "support_matrix.yaml"
        _write_yaml(props_path, {"properties": []})
        _write_yaml(
            support_path,
            {
                "support": [
                    {
                        "property_id": "display_flex",
                        "client_id": "gmail_web",
                        "level": "none",
                        "notes": "",
                        "fallback_ids": [],
                        "workaround": "",
                    }
                ]
            },
        )

        diff = SyncDiff(updated_support=[("display_flex", "gmail_web", "none", "full")])

        with (
            patch("app.knowledge.ontology.sync.writer._DATA_DIR", tmp_path),
            patch("app.knowledge.ontology.sync.writer.load_ontology"),
        ):
            result = apply_sync([], diff)

        assert result == 1

        with support_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["support"][0]["level"] == "full"

    def test_appends_new_support_entries(self, tmp_path: Path) -> None:
        props_path = tmp_path / "css_properties.yaml"
        support_path = tmp_path / "support_matrix.yaml"
        _write_yaml(props_path, {"properties": []})
        _write_yaml(support_path, {"support": []})

        diff = SyncDiff(new_support=[("display_flex", "gmail_web", "partial")])

        with (
            patch("app.knowledge.ontology.sync.writer._DATA_DIR", tmp_path),
            patch("app.knowledge.ontology.sync.writer.load_ontology"),
        ):
            result = apply_sync([], diff)

        assert result == 1

        with support_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert len(data["support"]) == 1
        assert data["support"][0]["property_id"] == "display_flex"
        assert data["support"][0]["level"] == "partial"

    def test_cache_cleared_after_write(self, tmp_path: Path) -> None:
        props_path = tmp_path / "css_properties.yaml"
        support_path = tmp_path / "support_matrix.yaml"
        _write_yaml(props_path, {"properties": []})
        _write_yaml(support_path, {"support": []})

        diff = SyncDiff(new_support=[("p", "c", "full")])

        with (
            patch("app.knowledge.ontology.sync.writer._DATA_DIR", tmp_path),
            patch("app.knowledge.ontology.sync.writer.load_ontology") as mock_load,
        ):
            apply_sync([], diff)
            mock_load.cache_clear.assert_called_once()
