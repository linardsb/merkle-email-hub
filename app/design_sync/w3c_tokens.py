# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnnecessaryIsInstance=false
"""W3C Design Tokens v1.0 JSON parser.

Parses the W3C Design Tokens Community Group format (v1.0 stable, Oct 2025)
into ExtractedTokens for the design-to-email pipeline. Handles alias
resolution, multi-mode (light/dark), and composite token types.

Spec: https://design-tokens.github.io/community-group/format/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.design_sync.exceptions import W3cTokenParseError
from app.design_sync.protocol import (
    ExtractedColor,
    ExtractedGradient,
    ExtractedSpacing,
    ExtractedTokens,
    ExtractedTypography,
)
from app.design_sync.token_transforms import TokenWarning

logger = get_logger(__name__)

_MAX_NESTING_DEPTH = 20
_MAX_ALIAS_DEPTH = 10

_W3C_COLOR_TYPES = frozenset({"color"})
_W3C_DIMENSION_TYPES = frozenset({"dimension"})
_W3C_FONT_TYPES = frozenset({"fontFamily", "fontWeight", "fontSize"})
_W3C_GRADIENT_TYPES = frozenset({"gradient"})
_W3C_IGNORED_TYPES = frozenset({"duration", "cubicBezier", "strokeStyle", "transition"})
_W3C_KNOWN_TYPES = (
    _W3C_COLOR_TYPES
    | _W3C_DIMENSION_TYPES
    | _W3C_FONT_TYPES
    | _W3C_GRADIENT_TYPES
    | _W3C_IGNORED_TYPES
    | frozenset({"shadow", "border", "number"})
)

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
_HEX8_RE = re.compile(r"^#[0-9a-fA-F]{8}$")
_RGBA_RE = re.compile(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)$")
_DIMENSION_RE = re.compile(r"^(-?[\d.]+)\s*(px|rem|em)$")
_ALIAS_RE = re.compile(r"^\{(.+)\}$")


@dataclass
class _CollectedTokens:
    """Mutable accumulator used during tree walk."""

    colors: list[ExtractedColor] = field(default_factory=list)
    typography: list[ExtractedTypography] = field(default_factory=list)
    spacing: list[ExtractedSpacing] = field(default_factory=list)
    gradients: list[ExtractedGradient] = field(default_factory=list)
    dark_colors: list[ExtractedColor] = field(default_factory=list)
    warnings: list[TokenWarning] = field(default_factory=list)
    font_parts: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class W3cParseResult:
    """Result of parsing W3C Design Tokens JSON."""

    tokens: ExtractedTokens
    warnings: list[TokenWarning]


def parse_w3c_tokens(tokens_json: dict[str, Any]) -> W3cParseResult:
    """Parse W3C Design Tokens v1.0 JSON into ExtractedTokens.

    Args:
        tokens_json: W3C format dict with ``$type``/``$value`` entries.

    Returns:
        W3cParseResult with extracted tokens and any warnings.

    Raises:
        W3cTokenParseError: If the JSON fails basic schema validation.
    """
    errors = _validate_w3c_schema(tokens_json)
    if errors:
        raise W3cTokenParseError(f"Invalid W3C tokens: {'; '.join(errors[:5])}")

    collected = _CollectedTokens()
    _walk_tokens(tokens_json, "", tokens_json, depth=0, collected=collected)

    # Merge font parts into typography tokens
    _merge_font_parts(collected)

    # Collect dark mode colors from $extensions.mode
    dark = _collect_dark_mode(tokens_json, tokens_json, collected.warnings)
    collected.dark_colors.extend(dark)

    tokens = ExtractedTokens(
        colors=collected.colors,
        typography=collected.typography,
        spacing=collected.spacing,
        gradients=collected.gradients,
        dark_colors=collected.dark_colors,
    )

    logger.info(
        "design_sync.w3c_tokens_parsed",
        colors=len(collected.colors),
        typography=len(collected.typography),
        spacing=len(collected.spacing),
        gradients=len(collected.gradients),
        dark_colors=len(collected.dark_colors),
        warnings=len(collected.warnings),
    )

    return W3cParseResult(tokens=tokens, warnings=collected.warnings)


def _validate_w3c_schema(obj: dict[str, Any], depth: int = 0) -> list[str]:
    """Validate basic W3C schema constraints. Returns list of error messages."""
    errors: list[str] = []

    if not isinstance(obj, dict):
        errors.append("Root must be a JSON object")
        return errors

    if depth > _MAX_NESTING_DEPTH:
        errors.append(f"Nesting depth exceeds maximum of {_MAX_NESTING_DEPTH}")
        return errors

    for key, value in obj.items():
        if key.startswith("$"):
            continue
        if isinstance(value, dict):
            token_type = value.get("$type")
            if token_type is not None and token_type not in _W3C_KNOWN_TYPES:
                errors.append(f"Unknown $type '{token_type}' at '{key}'")
            child_errors = _validate_w3c_schema(value, depth + 1)
            errors.extend(child_errors)

    return errors


def _resolve_alias(
    ref: str,
    root: dict[str, Any],
    *,
    visited: frozenset[str] = frozenset(),
) -> tuple[Any, str | None]:
    """Resolve ``{path.to.token}`` alias references with cycle detection.

    Returns:
        (resolved_value, error_message_or_None)
    """
    if ref in visited:
        return None, f"Circular alias detected: {ref}"

    if len(visited) >= _MAX_ALIAS_DEPTH:
        return None, f"Alias chain exceeds maximum depth of {_MAX_ALIAS_DEPTH}: {ref}"

    parts = ref.split(".")
    current: Any = root
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None, f"Alias target not found: {ref}"
        current = current[part]

    if isinstance(current, dict):
        value = current.get("$value")
        if value is None:
            return None, f"Alias target has no $value: {ref}"
        # Check if the resolved value is itself an alias
        if isinstance(value, str):
            alias_match = _ALIAS_RE.match(value)
            if alias_match:
                return _resolve_alias(
                    alias_match.group(1),
                    root,
                    visited=visited | {ref},
                )
        return value, None

    return current, None


def _walk_tokens(
    obj: dict[str, Any],
    path: str,
    root: dict[str, Any],
    *,
    depth: int,
    collected: _CollectedTokens,
) -> None:
    """Recursively walk the token tree, collecting tokens by type."""
    if depth > _MAX_NESTING_DEPTH:
        collected.warnings.append(
            TokenWarning(
                level="error",
                field=path or "<root>",
                message=f"Nesting depth exceeds {_MAX_NESTING_DEPTH}",
            )
        )
        return

    # Inherit $type from parent groups
    inherited_type = obj.get("$type")

    for key, value in obj.items():
        if key.startswith("$"):
            continue
        if not isinstance(value, dict):
            continue

        current_path = f"{path}.{key}" if path else key
        token_type = value.get("$type", inherited_type)
        raw_value = value.get("$value")

        if raw_value is not None:
            # This is a token leaf — resolve alias if needed
            resolved = _resolve_value(raw_value, root, collected.warnings, current_path)
            if resolved is None:
                continue

            _handle_token(token_type, key, resolved, current_path, collected)
        else:
            # Group node — recurse, passing inherited type
            child = dict(value)
            if inherited_type and "$type" not in child:
                child["$type"] = inherited_type
            _walk_tokens(child, current_path, root, depth=depth + 1, collected=collected)


def _resolve_value(
    raw_value: Any,  # noqa: ANN401
    root: dict[str, Any],
    warnings: list[TokenWarning],
    path: str,
) -> Any:  # noqa: ANN401
    """Resolve a $value, following aliases if present."""
    if isinstance(raw_value, str):
        alias_match = _ALIAS_RE.match(raw_value)
        if alias_match:
            resolved, error = _resolve_alias(alias_match.group(1), root)
            if error:
                warnings.append(TokenWarning(level="warning", field=path, message=error))
                return None
            return resolved
    return raw_value


def _handle_token(
    token_type: str | None,
    name: str,
    value: Any,  # noqa: ANN401
    path: str,
    collected: _CollectedTokens,
) -> None:
    """Route a resolved token to the appropriate collector."""
    if token_type is None:
        return

    if token_type in _W3C_COLOR_TYPES:
        color = _parse_color(name, value)
        if color:
            collected.colors.append(color)

    elif token_type in _W3C_DIMENSION_TYPES:
        spacing = _parse_dimension(name, value)
        if spacing:
            collected.spacing.append(spacing)

    elif token_type in _W3C_FONT_TYPES:
        # Accumulate font parts — they get merged later
        group = path.rsplit(".", 1)[0] if "." in path else name
        if group not in collected.font_parts:
            collected.font_parts[group] = {"_name": group.rsplit(".", 1)[-1]}
        collected.font_parts[group][token_type] = value

    elif token_type in _W3C_GRADIENT_TYPES:
        gradient = _parse_gradient(name, value)
        if gradient:
            collected.gradients.append(gradient)

    elif token_type in _W3C_IGNORED_TYPES:
        pass  # Non-email-relevant types

    elif token_type in {"shadow", "border"}:
        collected.warnings.append(
            TokenWarning(
                level="info",
                field=path,
                message=f"Composite type '{token_type}' skipped (not email-relevant)",
            )
        )

    elif token_type == "number":  # noqa: S105
        pass  # Raw numbers — context-dependent, skip

    else:
        collected.warnings.append(
            TokenWarning(
                level="warning",
                field=path,
                message=f"Unknown token type '{token_type}' skipped",
            )
        )


def _parse_color(name: str, value: Any) -> ExtractedColor | None:  # noqa: ANN401
    """Parse a W3C color value to ExtractedColor."""
    if not isinstance(value, str):
        return None

    value = value.strip()

    # #RRGGBB or #RGB
    if _HEX_RE.match(value):
        hex_val = _expand_hex(value)
        return ExtractedColor(name=name, hex=hex_val)

    # #RRGGBBAA
    if _HEX8_RE.match(value):
        hex_val = value[:7].upper()
        alpha = int(value[7:9], 16) / 255.0
        return ExtractedColor(name=name, hex=hex_val, opacity=round(alpha, 3))

    # rgba(R, G, B, A) or rgb(R, G, B)
    rgba_match = _RGBA_RE.match(value)
    if rgba_match:
        r, g, b = int(rgba_match.group(1)), int(rgba_match.group(2)), int(rgba_match.group(3))
        a = float(rgba_match.group(4)) if rgba_match.group(4) else 1.0
        hex_val = f"#{r:02X}{g:02X}{b:02X}"
        return ExtractedColor(name=name, hex=hex_val, opacity=round(a, 3))

    return None


def _expand_hex(value: str) -> str:
    """Expand 3-digit hex to 6-digit and uppercase."""
    v = value.lstrip("#")
    if len(v) == 3:
        v = v[0] * 2 + v[1] * 2 + v[2] * 2
    return f"#{v.upper()}"


def _parse_dimension(name: str, value: Any) -> ExtractedSpacing | None:  # noqa: ANN401
    """Parse a W3C dimension value to ExtractedSpacing."""
    if not isinstance(value, str):
        if isinstance(value, int | float):
            return ExtractedSpacing(name=name, value=float(value))
        return None

    match = _DIMENSION_RE.match(value.strip())
    if not match:
        return None

    num = float(match.group(1))
    unit = match.group(2)

    if unit == "rem":
        num *= 16.0  # Standard base font size
    elif unit == "em":
        num *= 16.0  # Approximate for email

    return ExtractedSpacing(name=name, value=num)


def _parse_gradient(name: str, value: Any) -> ExtractedGradient | None:  # noqa: ANN401
    """Parse a W3C gradient composite token."""
    if not isinstance(value, dict):
        return None

    gradient_type = str(value.get("type", "linear"))
    angle = float(value.get("angle", 180))

    raw_stops = value.get("stops")
    if not isinstance(raw_stops, list) or len(raw_stops) < 2:
        return None

    stops: list[tuple[str, float]] = []
    for stop in raw_stops:
        if not isinstance(stop, dict):
            continue
        color = str(stop.get("color", "#000000"))
        position = float(stop.get("position", 0.0))
        # Normalize color to hex
        parsed = _parse_color("_stop", color)
        hex_val = parsed.hex if parsed else "#000000"
        stops.append((hex_val, position))

    if len(stops) < 2:
        return None

    # Compute midpoint fallback for Outlook
    mid_idx = len(stops) // 2
    fallback_hex = stops[mid_idx][0]

    return ExtractedGradient(
        name=name,
        type=gradient_type,
        angle=angle,
        stops=tuple(stops),
        fallback_hex=fallback_hex,
    )


def _merge_font_parts(collected: _CollectedTokens) -> None:
    """Merge accumulated fontFamily/fontWeight/fontSize into ExtractedTypography."""
    for parts in collected.font_parts.values():
        name = parts.get("_name", "unknown")
        family = parts.get("fontFamily")
        if not family:
            continue

        weight = str(parts.get("fontWeight", "400"))
        size_raw = parts.get("fontSize")
        size = _dimension_to_px(size_raw) if size_raw else 16.0

        collected.typography.append(
            ExtractedTypography(
                name=name,
                family=family if isinstance(family, str) else str(family),
                weight=weight,
                size=size,
                line_height=round(size * 1.5, 1),  # Default 1.5x
            )
        )


def _dimension_to_px(value: Any) -> float:  # noqa: ANN401
    """Convert a dimension value to pixels."""
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        match = _DIMENSION_RE.match(value.strip())
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            if unit in ("rem", "em"):
                num *= 16.0
            return num
    return 16.0


def _collect_dark_mode(
    obj: dict[str, Any],
    root: dict[str, Any],
    warnings: list[TokenWarning],
    *,
    depth: int = 0,
) -> list[ExtractedColor]:
    """Extract dark mode colors from ``$extensions.mode`` entries."""
    if depth > _MAX_NESTING_DEPTH:
        return []

    dark_colors: list[ExtractedColor] = []

    extensions = obj.get("$extensions")
    if isinstance(extensions, dict):
        mode = extensions.get("mode")
        if isinstance(mode, dict):
            dark = mode.get("dark")
            if isinstance(dark, dict):
                _walk_dark_colors(dark, "", root, dark_colors, warnings)

    # Also check top-level groups for nested $extensions.mode
    for key, value in obj.items():
        if key.startswith("$") or not isinstance(value, dict):
            continue
        dark_colors.extend(_collect_dark_mode(value, root, warnings, depth=depth + 1))

    return dark_colors


def _walk_dark_colors(
    obj: dict[str, Any],
    path: str,
    root: dict[str, Any],
    dark_colors: list[ExtractedColor],
    warnings: list[TokenWarning],
    *,
    depth: int = 0,
) -> None:
    """Walk a dark mode group collecting color overrides."""
    if depth > _MAX_NESTING_DEPTH:
        return

    for key, value in obj.items():
        if key.startswith("$") or not isinstance(value, dict):
            continue

        current_path = f"{path}.{key}" if path else key
        raw_value = value.get("$value")

        if raw_value is not None:
            resolved = _resolve_value(raw_value, root, warnings, current_path)
            if resolved and isinstance(resolved, str):
                color = _parse_color(key, resolved)
                if color:
                    dark_colors.append(color)
        else:
            _walk_dark_colors(value, current_path, root, dark_colors, warnings, depth=depth + 1)
