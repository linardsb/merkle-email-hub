"""Client-aware CSS compatibility checks for design conversion."""

from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.ontology import OntologyRegistry, SupportLevel, get_ontology


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
    """

    def __init__(self, target_clients: list[str] | None = None) -> None:
        self._registry: OntologyRegistry = get_ontology()
        self._targets: list[str] = target_clients or []
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
        """
        if not self._targets:
            return SupportLevel.FULL

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

    def unsupported_clients(
        self,
        css_property: str,
        value: str | None = None,
    ) -> list[str]:
        """Return target client IDs that do NOT support this property."""
        if not self._targets:
            return []

        prop = self._registry.find_property_by_name(css_property, value)
        if prop is None:
            return []

        result: list[str] = []
        for client_id in self._targets:
            level = self._registry.get_support(prop.id, client_id)
            if level == SupportLevel.NONE:
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
