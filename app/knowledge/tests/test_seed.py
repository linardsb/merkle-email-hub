"""Tests for knowledge base seed manifest and file integrity."""

from pathlib import Path

import pytest

from app.knowledge.data.seed_manifest import ALLOWED_DOMAINS, SEED_MANIFEST, SeedEntry

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"


class TestSeedManifest:
    """Validate seed manifest structure and completeness."""

    def test_manifest_is_not_empty(self) -> None:
        assert len(SEED_MANIFEST) == 20

    def test_all_entries_are_seed_entry(self) -> None:
        for entry in SEED_MANIFEST:
            assert isinstance(entry, SeedEntry)

    def test_all_domains_are_valid(self) -> None:
        for entry in SEED_MANIFEST:
            assert entry.domain in ALLOWED_DOMAINS, (
                f"{entry.filename} has invalid domain '{entry.domain}'"
            )

    def test_all_titles_are_non_empty(self) -> None:
        for entry in SEED_MANIFEST:
            assert entry.title.strip(), f"{entry.filename} has empty title"

    def test_all_descriptions_are_non_empty(self) -> None:
        for entry in SEED_MANIFEST:
            assert entry.description.strip(), f"{entry.filename} has empty description"

    def test_all_tags_are_non_empty(self) -> None:
        for entry in SEED_MANIFEST:
            assert len(entry.tags) > 0, f"{entry.filename} has no tags"
            for tag in entry.tags:
                assert tag.strip(), f"{entry.filename} has blank tag"

    def test_no_duplicate_filenames(self) -> None:
        filenames = [e.filename for e in SEED_MANIFEST]
        assert len(filenames) == len(set(filenames)), "Duplicate filenames in manifest"

    def test_domain_counts(self) -> None:
        counts: dict[str, int] = {}
        for entry in SEED_MANIFEST:
            counts[entry.domain] = counts.get(entry.domain, 0) + 1
        assert counts["css_support"] == 8
        assert counts["best_practices"] == 6
        assert counts["client_quirks"] == 6


class TestSeedFiles:
    """Validate seed markdown files exist and are readable."""

    @pytest.mark.parametrize(
        "entry",
        SEED_MANIFEST,
        ids=[e.filename for e in SEED_MANIFEST],
    )
    def test_file_exists(self, entry: SeedEntry) -> None:
        file_path = SEED_DIR / entry.filename
        assert file_path.is_file(), f"Missing seed file: {entry.filename}"

    @pytest.mark.parametrize(
        "entry",
        SEED_MANIFEST,
        ids=[e.filename for e in SEED_MANIFEST],
    )
    def test_file_is_valid_utf8_and_non_empty(self, entry: SeedEntry) -> None:
        file_path = SEED_DIR / entry.filename
        content = file_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 100, f"{entry.filename} is too short ({len(content)} chars)"

    @pytest.mark.parametrize(
        "entry",
        SEED_MANIFEST,
        ids=[e.filename for e in SEED_MANIFEST],
    )
    def test_file_starts_with_heading(self, entry: SeedEntry) -> None:
        file_path = SEED_DIR / entry.filename
        content = file_path.read_text(encoding="utf-8")
        assert content.startswith("# "), f"{entry.filename} must start with a # heading"

    @pytest.mark.parametrize(
        "entry",
        SEED_MANIFEST,
        ids=[e.filename for e in SEED_MANIFEST],
    )
    def test_file_has_overview_section(self, entry: SeedEntry) -> None:
        file_path = SEED_DIR / entry.filename
        content = file_path.read_text(encoding="utf-8")
        assert "## Overview" in content, f"{entry.filename} missing ## Overview section"

    @pytest.mark.parametrize(
        "entry",
        SEED_MANIFEST,
        ids=[e.filename for e in SEED_MANIFEST],
    )
    def test_file_has_key_takeaways(self, entry: SeedEntry) -> None:
        file_path = SEED_DIR / entry.filename
        content = file_path.read_text(encoding="utf-8")
        assert "## Key Takeaways" in content, f"{entry.filename} missing ## Key Takeaways section"

    def test_filename_matches_directory(self) -> None:
        """Each entry's filename path should start with its domain."""
        for entry in SEED_MANIFEST:
            assert entry.filename.startswith(entry.domain + "/"), (
                f"{entry.filename} doesn't match domain {entry.domain}"
            )
