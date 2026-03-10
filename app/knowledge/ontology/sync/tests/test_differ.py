"""Tests for ontology diff computation."""

from unittest.mock import MagicMock

from app.knowledge.ontology.sync.differ import compute_diff
from app.knowledge.ontology.sync.schemas import CanIEmailFeature
from app.knowledge.ontology.types import SupportEntry, SupportLevel


def _make_feature(
    slug: str = "css-display-flex",
    title: str = "display:flex",
    stats: dict[str, dict[str, dict[str, str]]] | None = None,
) -> CanIEmailFeature:
    return CanIEmailFeature(
        slug=slug,
        title=title,
        category="css",
        last_test_date="2024-01-01",
        stats=stats or {},
        notes={},
    )


def _make_entry(prop_id: str, client_id: str, level: SupportLevel) -> SupportEntry:
    return SupportEntry(property_id=prop_id, client_id=client_id, level=level)


def _make_registry(
    property_ids: list[str] | None = None,
    client_ids: list[str] | None = None,
    entries: dict[tuple[str, str], SupportEntry] | None = None,
) -> MagicMock:
    """Create a mock OntologyRegistry."""
    registry = MagicMock()
    registry.property_ids.return_value = property_ids or []
    registry.client_ids.return_value = client_ids or []

    def get_support_entry(prop_id: str, client_id: str) -> SupportEntry | None:
        if entries:
            return entries.get((prop_id, client_id))
        return None

    registry.get_support_entry = get_support_entry
    return registry


class TestComputeDiff:
    def test_no_changes_explicit_full(self) -> None:
        """Explicit FULL entry + incoming FULL = unchanged."""
        entry = _make_entry("display_flex", "gmail_web", SupportLevel.FULL)
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={("display_flex", "gmail_web"): entry},
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert not diff.has_changes
        assert diff.unchanged_count == 1

    def test_no_changes_implicit_full(self) -> None:
        """No explicit entry + incoming FULL = unchanged (default is FULL)."""
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={},
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert not diff.has_changes
        assert diff.unchanged_count == 1

    def test_new_property_detected(self) -> None:
        registry = _make_registry(
            property_ids=[],
            client_ids=["gmail_web"],
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert "display_flex" in diff.new_properties
        assert diff.has_changes

    def test_updated_support_level(self) -> None:
        """Explicit NONE entry + incoming FULL = updated_support."""
        entry = _make_entry("display_flex", "gmail_web", SupportLevel.NONE)
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={("display_flex", "gmail_web"): entry},
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert len(diff.updated_support) == 1
        _prop_id, _client_id, old, new = diff.updated_support[0]
        assert old == "none"
        assert new == "full"

    def test_new_support_from_unknown(self) -> None:
        """Explicit UNKNOWN entry + incoming FULL = new_support."""
        entry = _make_entry("display_flex", "gmail_web", SupportLevel.UNKNOWN)
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={("display_flex", "gmail_web"): entry},
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert len(diff.new_support) == 1
        assert diff.has_changes

    def test_no_entry_incoming_none_creates_new_support(self) -> None:
        """No explicit entry + incoming NONE = new_support (not dropped)."""
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={},  # No entry → default FULL
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "n"}}},
        )
        diff = compute_diff(registry, [feat])
        # Should be new_support, not updated_support (no entry to update)
        assert len(diff.new_support) == 1
        assert len(diff.updated_support) == 0
        assert diff.has_changes

    def test_new_client_detected(self) -> None:
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=[],
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert "gmail_web" in diff.new_clients

    def test_diff_has_changes_flag_false(self) -> None:
        entry = _make_entry("display_flex", "gmail_web", SupportLevel.FULL)
        registry = _make_registry(
            property_ids=["display_flex"],
            client_ids=["gmail_web"],
            entries={("display_flex", "gmail_web"): entry},
        )
        feat = _make_feature(
            stats={"gmail": {"desktop-webmail": {"2024-01": "y"}}},
        )
        diff = compute_diff(registry, [feat])
        assert not diff.has_changes
