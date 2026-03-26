"""Email client rendering matrix — loads YAML, builds indexed lookups."""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from app.core.logging import get_logger
from app.knowledge.ontology.types import ClientEngine, SupportLevel

logger = get_logger(__name__)
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Map YAML engine strings to ClientEngine enum values
_ENGINE_MAP: dict[str, ClientEngine] = {
    "webkit": ClientEngine.WEBKIT,
    "blink": ClientEngine.BLINK,
    "blink_restricted": ClientEngine.BLINK,
    "word": ClientEngine.WORD,
    "gecko": ClientEngine.GECKO,
    "presto": ClientEngine.PRESTO,
    "custom": ClientEngine.CUSTOM,
    "webview": ClientEngine.CUSTOM,
}

_SUPPORT_MAP: dict[str, SupportLevel] = {
    "full": SupportLevel.FULL,
    "partial": SupportLevel.PARTIAL,
    "none": SupportLevel.NONE,
    "unknown": SupportLevel.UNKNOWN,
}


# ── Models ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CSSSupport:
    """CSS property support level for a specific client."""

    support: SupportLevel
    workaround: str = ""
    notes: str = ""


DarkModeType = Literal[
    "forced_inversion",
    "partial_inversion",
    "partial_developer",
    "developer_controlled",
    "double_inversion_risk",
    "unknown",
]
DeveloperControl = Literal["none", "partial", "full", "limited", "unknown"]


@dataclass(frozen=True)
class DarkModeProfile:
    """Dark mode behavior for an email client."""

    type: DarkModeType
    developer_control: DeveloperControl
    selectors: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class KnownBug:
    """Known rendering bug for an email client."""

    id: str
    symptom: str
    fix: str


@dataclass(frozen=True)
class SizeLimits:
    """Message size limits for an email client."""

    clip_threshold_kb: int | None = None
    style_block: str = ""


@dataclass(frozen=True)
class ClientProfile:
    """Complete rendering profile for an email client."""

    id: str
    display_name: str
    engine: ClientEngine
    css_support: dict[str, dict[str, CSSSupport]]  # category → prop → CSSSupport
    dark_mode: DarkModeProfile
    vml_required: bool = False
    mso_conditionals: bool = False
    known_bugs: tuple[KnownBug, ...] = ()
    size_limits: SizeLimits = field(default_factory=SizeLimits)
    supported_fonts: tuple[str, ...] | str = "*"


@dataclass(frozen=True)
class AudienceConstraints:
    """Aggregated lowest-common-denominator constraints for a set of clients."""

    unsupported_properties: tuple[tuple[str, str, str], ...]  # (category, prop, workaround)
    dark_mode_types: tuple[str, ...]
    dark_mode_selectors: tuple[str, ...]
    vml_required: bool
    mso_conditionals: bool
    known_bugs: tuple[KnownBug, ...]
    clip_threshold_kb: int | None
    rendering_engines: tuple[str, ...]


# ── Registry ────────────────────────────────────────────────────────


class ClientMatrix:
    """Indexed lookup registry for the email client rendering matrix."""

    __slots__ = ("_by_id", "clients", "version")

    def __init__(self, *, clients: tuple[ClientProfile, ...], version: str) -> None:
        self.clients = clients
        self.version = version
        self._by_id: dict[str, ClientProfile] = {c.id: c for c in clients}

    def get_client(self, client_id: str) -> ClientProfile | None:
        """Lookup a single client by ID."""
        return self._by_id.get(client_id)

    def get_css_support(self, client_id: str, property_name: str) -> CSSSupport | None:
        """Lookup CSS property support for a client (searches all categories)."""
        client = self._by_id.get(client_id)
        if not client:
            return None
        for category_props in client.css_support.values():
            if property_name in category_props:
                return category_props[property_name]
        return None

    def get_dark_mode(self, client_id: str) -> DarkModeProfile | None:
        """Get dark mode behavior for a client."""
        client = self._by_id.get(client_id)
        return client.dark_mode if client else None

    def get_known_bugs(self, client_id: str) -> list[KnownBug]:
        """Get known rendering bugs for a client."""
        client = self._by_id.get(client_id)
        return list(client.known_bugs) if client else []

    def get_constraints_for_clients(self, client_ids: list[str]) -> AudienceConstraints:
        """Aggregate constraints — intersection = lowest common denominator."""
        unsupported: list[tuple[str, str, str]] = []
        dm_types: set[str] = set()
        dm_selectors: set[str] = set()
        vml = False
        mso = False
        bugs: list[KnownBug] = []
        bug_ids: set[str] = set()
        clip_kb: int | None = None
        engines: set[str] = set()

        for cid in client_ids:
            client = self._by_id.get(cid)
            if not client:
                continue

            engines.add(client.engine.value)

            # Collect unsupported CSS properties
            for category, props in client.css_support.items():
                for prop_name, css in props.items():
                    if css.support in (SupportLevel.NONE, SupportLevel.PARTIAL):
                        unsupported.append((category, prop_name, css.workaround))

            # Dark mode
            dm_types.add(client.dark_mode.type)
            for sel in client.dark_mode.selectors:
                dm_selectors.add(sel)

            # VML / MSO
            if client.vml_required:
                vml = True
            if client.mso_conditionals:
                mso = True

            # Bugs (deduplicate by id)
            for bug in client.known_bugs:
                if bug.id not in bug_ids:
                    bug_ids.add(bug.id)
                    bugs.append(bug)

            # Size limits (take the smallest clip threshold)
            if client.size_limits.clip_threshold_kb is not None and (
                clip_kb is None or client.size_limits.clip_threshold_kb < clip_kb
            ):
                clip_kb = client.size_limits.clip_threshold_kb

        # Deduplicate unsupported (same category+prop from different clients)
        seen: set[tuple[str, str]] = set()
        deduped: list[tuple[str, str, str]] = []
        for cat, prop, wa in unsupported:
            key = (cat, prop)
            if key not in seen:
                seen.add(key)
                deduped.append((cat, prop, wa))

        return AudienceConstraints(
            unsupported_properties=tuple(deduped),
            dark_mode_types=tuple(sorted(dm_types)),
            dark_mode_selectors=tuple(sorted(dm_selectors)),
            vml_required=vml,
            mso_conditionals=mso,
            known_bugs=tuple(bugs),
            clip_threshold_kb=clip_kb,
            rendering_engines=tuple(sorted(engines)),
        )

    def format_audience_context(self, client_ids: list[str]) -> str:
        """Generate rendering-specific audience constraint lines.

        Returns lines to append to the existing ontology-based audience
        context string (engine warnings, size limits, dark mode types).
        """
        constraints = self.get_constraints_for_clients(client_ids)
        parts: list[str] = []

        # Rendering engines
        if constraints.rendering_engines:
            parts.append(f"\nRENDERING ENGINES: {', '.join(constraints.rendering_engines)}")

        # VML / MSO requirements
        if constraints.vml_required:
            parts.append(
                "REQUIREMENT: VML required — use <v:roundrect> for buttons, "
                "<v:fill> for background images (Outlook Word engine)"
            )
        if constraints.mso_conditionals:
            parts.append(
                "REQUIREMENT: MSO conditional comments required — "
                "<!--[if mso]> ghost tables for multi-column layout"
            )

        # Size limits
        if constraints.clip_threshold_kb:
            parts.append(
                f"WARNING: Message clipping at {constraints.clip_threshold_kb}KB "
                "(Gmail) — keep total HTML under this limit"
            )

        # Dark mode types
        if constraints.dark_mode_types:
            dm_summary = ", ".join(sorted(constraints.dark_mode_types))
            parts.append(f"\nDARK MODE TYPES: {dm_summary}")
            if constraints.dark_mode_selectors:
                parts.append(
                    "  Supported selectors: " + ", ".join(sorted(constraints.dark_mode_selectors))
                )

        # Known bugs
        if constraints.known_bugs:
            parts.append("\nKNOWN RENDERING BUGS:")
            for bug in constraints.known_bugs:
                parts.append(f"  - {bug.id}: {bug.symptom} → {bug.fix}")

        return "\n".join(parts)


# ── YAML Parser ─────────────────────────────────────────────────────


def _parse_css_support(raw: dict[str, Any]) -> dict[str, dict[str, CSSSupport]]:
    """Parse nested CSS support structure from YAML."""
    result: dict[str, dict[str, CSSSupport]] = {}
    for category, props in raw.items():
        if not isinstance(props, dict):
            continue
        result[category] = {}
        for prop_name, spec in props.items():
            if isinstance(spec, dict):
                level = _SUPPORT_MAP.get(spec.get("support", "unknown"), SupportLevel.UNKNOWN)
                result[category][prop_name] = CSSSupport(
                    support=level,
                    workaround=spec.get("workaround", ""),
                    notes=spec.get("notes", ""),
                )
    return result


def _parse_dark_mode(raw: dict[str, Any]) -> DarkModeProfile:
    """Parse dark mode profile from YAML."""
    selectors = raw.get("selectors", [])
    # Validate against Literal types, default to "unknown" if unrecognized
    dm_type: DarkModeType = raw.get("type", "unknown")  # type: ignore[assignment]
    dev_ctrl: DeveloperControl = raw.get("developer_control", "unknown")  # type: ignore[assignment]
    return DarkModeProfile(
        type=dm_type,
        developer_control=dev_ctrl,
        selectors=tuple(selectors) if isinstance(selectors, list) else (),
        notes=raw.get("notes", ""),
    )


def _parse_known_bugs(raw: list[dict[str, str]]) -> tuple[KnownBug, ...]:
    """Parse known bugs list from YAML."""
    return tuple(
        KnownBug(
            id=bug.get("id", ""),
            symptom=bug.get("symptom", ""),
            fix=bug.get("fix", ""),
        )
        for bug in raw
    )


def _parse_size_limits(raw: dict[str, Any]) -> SizeLimits:
    """Parse size limits from YAML."""
    clip = raw.get("clip_threshold_kb")
    return SizeLimits(
        clip_threshold_kb=int(clip) if clip is not None else None,
        style_block=raw.get("style_block", ""),
    )


def _parse_supported_fonts(raw: str | list[str] | None) -> tuple[str, ...] | str:
    """Parse supported fonts — either '*' / 'system' or a list."""
    if isinstance(raw, list):
        return tuple(str(f) for f in raw)
    return str(raw) if raw else "*"


def _parse_client(client_id: str, raw: dict[str, Any]) -> ClientProfile:
    """Parse a single client profile from YAML."""
    engine_str = raw.get("engine", "custom")
    engine = _ENGINE_MAP.get(engine_str, ClientEngine.CUSTOM)

    css_raw = raw.get("css_support", {})
    css_support = _parse_css_support(css_raw) if isinstance(css_raw, dict) else {}

    dm_raw = raw.get("dark_mode", {})
    dark_mode = (
        _parse_dark_mode(dm_raw)
        if isinstance(dm_raw, dict)
        else DarkModeProfile(
            type="unknown",
            developer_control="unknown",
        )
    )

    bugs_raw = raw.get("known_bugs", [])
    known_bugs = _parse_known_bugs(bugs_raw) if isinstance(bugs_raw, list) else ()

    sl_raw = raw.get("size_limits", {})
    size_limits = _parse_size_limits(sl_raw) if isinstance(sl_raw, dict) else SizeLimits()

    return ClientProfile(
        id=client_id,
        display_name=raw.get("display_name", client_id),
        engine=engine,
        css_support=css_support,
        dark_mode=dark_mode,
        vml_required=bool(raw.get("vml_required", False)),
        mso_conditionals=bool(raw.get("mso_conditionals", False)),
        known_bugs=known_bugs,
        size_limits=size_limits,
        supported_fonts=_parse_supported_fonts(raw.get("supported_fonts", "*")),
    )


def _parse_yaml(raw: dict[str, Any]) -> ClientMatrix:
    """Parse full YAML dict into a ClientMatrix."""
    version = str(raw.get("version", "0.0"))
    clients_raw = raw.get("clients", {})

    profiles: list[ClientProfile] = []
    if isinstance(clients_raw, dict):
        for client_id, client_data in clients_raw.items():
            if isinstance(client_data, dict):
                profiles.append(_parse_client(client_id, client_data))

    return ClientMatrix(clients=tuple(profiles), version=version)


# ── Public API ──────────────────────────────────────────────────────


@functools.lru_cache(maxsize=1)
def load_client_matrix(
    path: Path | None = None,
) -> ClientMatrix:
    """Load and cache the email client rendering matrix from YAML.

    Uses ``@lru_cache`` for singleton caching — call
    ``load_client_matrix.cache_clear()`` in tests.
    """
    yaml_path = path or (_DATA_DIR / "email-client-matrix.yaml")
    if not yaml_path.exists():
        logger.warning(
            "knowledge.client_matrix_not_found",
            path=str(yaml_path),
        )
        return ClientMatrix(clients=(), version="0.0")

    with yaml_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        logger.warning("knowledge.client_matrix_invalid_format")
        return ClientMatrix(clients=(), version="0.0")

    matrix = _parse_yaml(raw)
    logger.info(
        "knowledge.client_matrix_loaded",
        version=matrix.version,
        client_count=len(matrix.clients),
    )
    return matrix
