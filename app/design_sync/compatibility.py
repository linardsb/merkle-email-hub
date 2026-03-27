"""Client-aware CSS compatibility checks for design conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.knowledge.ontology import OntologyRegistry, SupportLevel, get_ontology

if TYPE_CHECKING:
    from app.design_sync.caniemail import CanieMailData


@dataclass(frozen=True)
class CompatibilityHint:
    """A client compatibility observation surfaced during conversion."""

    level: str  # "info" | "warning"
    css_property: str
    message: str
    affected_clients: tuple[str, ...]


class ConverterCompatibility:
    """Read-only ontology lookup for the design converter.

    Not a compiler — does not mutate CSS. Answers "is this safe?" and
    "who won't support this?" so the converter can make informed choices
    and surface early warnings.

    Optionally merges caniemail.com data for broader feature coverage.
    """

    def __init__(
        self,
        target_clients: list[str] | None = None,
        *,
        caniemail_data: CanieMailData | None = None,
    ) -> None:
        self._registry: OntologyRegistry = get_ontology()
        self._targets: list[str] = target_clients or []
        self._caniemail: CanieMailData | None = caniemail_data
        self._hints: list[CompatibilityHint] = []

    @property
    def hints(self) -> list[CompatibilityHint]:
        return list(self._hints)

    @property
    def has_targets(self) -> bool:
        return len(self._targets) > 0

    def check_property(
        self,
        css_property: str,
        value: str | None = None,
    ) -> SupportLevel:
        """Check worst-case support for a CSS property across target clients.

        Returns SupportLevel.FULL if no targets configured (optimistic default).
        Merges ontology and caniemail data, using the more restrictive level.
        """
        if not self._targets:
            return SupportLevel.FULL

        ontology_level = self._check_ontology(css_property, value)
        caniemail_level = self._check_caniemail(css_property)

        # Use the more restrictive (lower) support level
        return min(ontology_level, caniemail_level, key=_support_level_rank)

    def check_property_with_source(
        self,
        css_property: str,
        value: str | None = None,
    ) -> tuple[SupportLevel, str]:
        """Check support and return which source determined the level.

        Returns:
            (support_level, source) where source is "ontology", "caniemail", or "both".
        """
        if not self._targets:
            return SupportLevel.FULL, "ontology"

        ontology_level = self._check_ontology(css_property, value)
        caniemail_level = self._check_caniemail(css_property)

        ontology_rank = _support_level_rank(ontology_level)
        caniemail_rank = _support_level_rank(caniemail_level)

        if ontology_rank == caniemail_rank:
            source = "both" if self._caniemail else "ontology"
        elif ontology_rank < caniemail_rank:
            source = "ontology"
        else:
            source = "caniemail"

        level = min(ontology_level, caniemail_level, key=_support_level_rank)
        return level, source

    def _check_ontology(
        self,
        css_property: str,
        value: str | None = None,
    ) -> SupportLevel:
        """Check support using the ontology registry."""
        prop = self._registry.find_property_by_name(css_property, value)
        if prop is None:
            return SupportLevel.FULL  # Unknown property — assume safe

        worst = SupportLevel.FULL
        for client_id in self._targets:
            level = self._registry.get_support(prop.id, client_id)
            if level == SupportLevel.NONE:
                return SupportLevel.NONE  # Short-circuit
            if level == SupportLevel.PARTIAL:
                worst = SupportLevel.PARTIAL
        return worst

    def _check_caniemail(self, css_property: str) -> SupportLevel:
        """Check support using caniemail.com data."""
        if not self._caniemail or not self._targets:
            return SupportLevel.FULL

        worst = SupportLevel.FULL
        feature_map = self._caniemail.features.get(css_property)
        if feature_map is None:
            return SupportLevel.FULL

        for client_id in self._targets:
            entry = feature_map.get(client_id)
            if entry is None:
                continue
            if entry.support == "no":
                return SupportLevel.NONE
            if entry.support == "partial":
                worst = SupportLevel.PARTIAL

        return worst

    def unsupported_clients(
        self,
        css_property: str,
        value: str | None = None,
    ) -> list[str]:
        """Return target client IDs that do NOT support this property."""
        if not self._targets:
            return []

        result: list[str] = []

        # Check ontology
        prop = self._registry.find_property_by_name(css_property, value)
        if prop is not None:
            for client_id in self._targets:
                level = self._registry.get_support(prop.id, client_id)
                if level == SupportLevel.NONE:
                    result.append(client_id)

        # Check caniemail (add clients not already found via ontology)
        if self._caniemail:
            feature_map = self._caniemail.features.get(css_property)
            if feature_map:
                seen = set(result)
                for client_id in self._targets:
                    if client_id in seen:
                        continue
                    entry = feature_map.get(client_id)
                    if entry and entry.support == "no":
                        result.append(client_id)

        return result

    def client_engine(self, client_id: str) -> str | None:
        """Get rendering engine name for a client (e.g., 'word', 'webkit')."""
        client = self._registry.get_client(client_id)
        return client.engine.value if client else None

    def warn(
        self,
        css_property: str,
        message: str,
        affected_clients: list[str] | None = None,
    ) -> None:
        """Record a compatibility hint for later surfacing."""
        self._hints.append(
            CompatibilityHint(
                level="warning",
                css_property=css_property,
                message=message,
                affected_clients=tuple(affected_clients or []),
            )
        )

    def info(
        self,
        css_property: str,
        message: str,
        affected_clients: list[str] | None = None,
    ) -> None:
        """Record an informational hint."""
        self._hints.append(
            CompatibilityHint(
                level="info",
                css_property=css_property,
                message=message,
                affected_clients=tuple(affected_clients or []),
            )
        )

    def check_and_warn(
        self,
        css_property: str,
        value: str | None = None,
        context: str = "",
    ) -> SupportLevel:
        """Check property support and auto-record warning if unsupported.

        Convenience method combining check_property() + warn().
        Returns the support level for conditional emission.
        """
        level = self.check_property(css_property, value)
        if level == SupportLevel.NONE:
            affected = self.unsupported_clients(css_property, value)
            client_names = ", ".join(affected[:3])
            suffix = f" +{len(affected) - 3} more" if len(affected) > 3 else ""
            prop_display = f"{css_property}: {value}" if value else css_property
            msg = f"{prop_display} not supported in {client_names}{suffix}"
            if context:
                msg = f"{context} — {msg}"
            self.warn(css_property, msg, affected)
        elif level == SupportLevel.PARTIAL:
            prop = self._registry.find_property_by_name(css_property, value)
            if prop is not None:
                affected = [
                    cid
                    for cid in self._targets
                    if self._registry.get_support(prop.id, cid) == SupportLevel.PARTIAL
                ]
                if affected:
                    client_names = ", ".join(affected[:3])
                    prop_display = f"{css_property}: {value}" if value else css_property
                    msg = f"{prop_display} has partial support in {client_names}"
                    if context:
                        msg = f"{context} — {msg}"
                    self.info(css_property, msg, affected)
        return level


_SUPPORT_RANK: dict[SupportLevel, int] = {
    SupportLevel.NONE: 0,
    SupportLevel.PARTIAL: 1,
    SupportLevel.FULL: 2,
}


def _support_level_rank(level: SupportLevel) -> int:
    """Numeric rank for SupportLevel comparison (lower = more restrictive)."""
    return _SUPPORT_RANK.get(level, 2)
