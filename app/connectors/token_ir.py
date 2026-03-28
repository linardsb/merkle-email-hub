"""ESP-agnostic token intermediate representation.

Parses any ESP's personalisation syntax into normalized IR nodes,
emits from IR to any target ESP syntax. Foundation for cross-ESP
token rewriting.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal, cast, get_args

from app.core.exceptions import DomainValidationError
from app.core.logging import get_logger
from app.qa_engine.personalisation_validator import (
    detect_platform as _detect_platform,
)

logger = get_logger(__name__)

ESPPlatform = Literal[
    "braze",
    "sfmc",
    "adobe_campaign",
    "klaviyo",
    "hubspot",
    "mailchimp",
    "sendgrid",
    "activecampaign",
    "iterable",
    "brevo",
]

ALL_PLATFORMS: Final[frozenset[str]] = frozenset(get_args(ESPPlatform))


@dataclass(frozen=True, slots=True)
class FilterExpr:
    name: str  # normalized: "default", "uppercase", "lowercase", "date", "truncate"
    args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VariableToken:
    name: str  # normalized ESP-agnostic name
    filters: tuple[FilterExpr, ...]
    fallback: str | None
    source_syntax: str  # original raw token string
    source_span: tuple[int, int]  # char offsets in source HTML


ConditionOp = Literal["exists", "eq", "neq", "gt", "lt", "contains"]


@dataclass(frozen=True, slots=True)
class ConditionalToken:
    variable: str
    operator: ConditionOp
    value: str | None
    body_html: str
    else_html: str | None
    source_span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class LoopToken:
    item_name: str  # "item"
    collection: str  # "event.items"
    body_html: str
    source_span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class TokenIR:
    variables: tuple[VariableToken, ...]
    conditionals: tuple[ConditionalToken, ...]
    loops: tuple[LoopToken, ...]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_LIQUID_VAR: Final = re.compile(r"\{\{\s*(.+?)\s*\}\}")
_LIQUID_IF: Final = re.compile(
    r"\{%[-\s]*if\s+(.+?)\s*[-]?%\}([\s\S]*?)(?:\{%[-\s]*else\s*[-]?%\}([\s\S]*?))?\{%[-\s]*endif\s*[-]?%\}"
)
_LIQUID_FOR: Final = re.compile(
    r"\{%[-\s]*for\s+(\w+)\s+in\s+([\w.]+)\s*[-]?%\}([\s\S]*?)\{%[-\s]*endfor\s*[-]?%\}"
)


def _normalize_name(name: str, prefixes: tuple[str, ...] = ()) -> str:
    """Strip platform-specific prefixes from variable names."""
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return name.strip()


def _parse_liquid_filters(raw_filter_chain: str) -> tuple[tuple[FilterExpr, ...], str | None]:
    """Parse a Liquid/Django/HubL filter chain after the variable name."""
    filters: list[FilterExpr] = []
    fallback: str | None = None

    parts = raw_filter_chain.split("|")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # filter_name: arg or filter_name(arg) or just filter_name
        if ":" in part:
            fname, _, farg = part.partition(":")
            fname = fname.strip()
            farg = farg.strip().strip("'\"")
        elif "(" in part:
            fname, _, rest = part.partition("(")
            fname = fname.strip()
            farg = rest.rstrip(")").strip().strip("'\"")
        else:
            fname = part
            farg = ""

        # Normalize filter names
        normalized = _FILTER_NORMALIZE.get(fname, fname)
        args = (farg,) if farg else ()
        if normalized == "default" and farg:
            fallback = farg
        filters.append(FilterExpr(name=normalized, args=args))

    return tuple(filters), fallback


_FILTER_NORMALIZE: Final[dict[str, str]] = {
    "default": "default",
    "upcase": "uppercase",
    "upper": "uppercase",
    "downcase": "lowercase",
    "lower": "lowercase",
    "date": "date",
    "datetimeformat": "date",
    "truncate": "truncate",
    "truncatechars": "truncate",
    "capitalize": "capitalize",
    "strip": "strip",
    "escape": "escape",
    "url_encode": "url_encode",
}


def _parse_liquid_condition(cond: str) -> tuple[str, ConditionOp, str | None]:
    """Parse a Liquid/Django condition like 'var == "val"' or just 'var'."""
    cond = cond.strip()
    _ops: list[tuple[str, ConditionOp]] = [
        ("!=", "neq"),
        ("==", "eq"),
        (">=", "gt"),
        ("<=", "lt"),
        (">", "gt"),
        ("<", "lt"),
        (" contains ", "contains"),
    ]
    for op_str, op_name in _ops:
        if op_str in cond:
            left, _, right = cond.partition(op_str)
            return left.strip(), op_name, right.strip().strip("'\"")
    return cond, "exists", None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_liquid_like(html: str, prefixes: tuple[str, ...] = ()) -> TokenIR:
    """Parse Liquid-like syntax (Braze, ActiveCampaign, Klaviyo, Brevo, HubSpot)."""
    variables: list[VariableToken] = []
    conditionals: list[ConditionalToken] = []
    loops: list[LoopToken] = []

    # Track spans consumed by conditionals/loops to avoid double-counting variables
    consumed: set[tuple[int, int]] = set()

    for m in _LIQUID_IF.finditer(html):
        cond_str = m.group(1)
        var, op, val = _parse_liquid_condition(cond_str)
        var = _normalize_name(var, prefixes)
        conditionals.append(
            ConditionalToken(
                variable=var,
                operator=op,
                value=val,
                body_html=m.group(2),
                else_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    for m in _LIQUID_FOR.finditer(html):
        loops.append(
            LoopToken(
                item_name=m.group(1),
                collection=_normalize_name(m.group(2), prefixes),
                body_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    for m in _LIQUID_VAR.finditer(html):
        # Skip variables inside consumed blocks (they're part of conditionals/loops tags)
        if any(s <= m.start() and m.end() <= e for s, e in consumed):
            continue
        # Skip logic tags that look like {{ but are actually {% %}
        content = m.group(1)
        if content.startswith(("%", "#")):
            continue
        # Split variable name from filters
        parts = content.split("|", 1)
        raw_name = parts[0].strip()
        name = _normalize_name(raw_name, prefixes)
        if not name:
            continue
        filter_chain = parts[1] if len(parts) > 1 else ""
        filters, fallback = _parse_liquid_filters(filter_chain)
        variables.append(
            VariableToken(
                name=name,
                filters=filters,
                fallback=fallback,
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )

    return TokenIR(
        variables=tuple(variables),
        conditionals=tuple(conditionals),
        loops=tuple(loops),
    )


def parse_braze(html: str) -> TokenIR:
    return _parse_liquid_like(html, prefixes=("${",))


def parse_klaviyo(html: str) -> TokenIR:
    return _parse_liquid_like(html, prefixes=("person.", "event."))


def parse_hubspot(html: str) -> TokenIR:
    return _parse_liquid_like(html, prefixes=("contact.", "company."))


def parse_activecampaign(html: str) -> TokenIR:
    return _parse_liquid_like(html, prefixes=("%",))


def parse_brevo(html: str) -> TokenIR:
    return _parse_liquid_like(html, prefixes=("contact.", "mirror."))


# ── SFMC (AMPscript) ──

_SFMC_OUTPUT: Final = re.compile(r"%%=v\((@?\w[\w.]*)\)=%%")
_SFMC_SET: Final = re.compile(r"SET\s+(@\w+)\s*=\s*(.+?)(?:\r?\n|$)", re.IGNORECASE)
_SFMC_IF: Final = re.compile(
    r"%%\[\s*IF\s+(.+?)\s+THEN\s*\]%%([\s\S]*?)(?:%%\[\s*ELSE\s*\]%%([\s\S]*?))?%%\[\s*ENDIF\s*\]%%",
    re.IGNORECASE,
)


def _parse_sfmc_condition(cond: str) -> tuple[str, ConditionOp, str | None]:
    cond = cond.strip()
    empty_match = re.match(r"Empty\s*\((@?\w+)\)", cond, re.IGNORECASE)
    if empty_match:
        return empty_match.group(1).lstrip("@"), "exists", None
    _ops: list[tuple[str, ConditionOp]] = [
        ("<>", "neq"),
        ("==", "eq"),
        (">=", "gt"),
        ("<=", "lt"),
        (">", "gt"),
        ("<", "lt"),
    ]
    for op_str, op_name in _ops:
        if op_str in cond:
            left, _, right = cond.partition(op_str)
            return left.strip().lstrip("@"), op_name, right.strip().strip("'\"")
    return cond.lstrip("@"), "exists", None


def parse_sfmc(html: str) -> TokenIR:
    variables: list[VariableToken] = []
    conditionals: list[ConditionalToken] = []

    for m in _SFMC_OUTPUT.finditer(html):
        name = m.group(1).lstrip("@")
        variables.append(
            VariableToken(
                name=name,
                filters=(),
                fallback=None,
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )

    for m in _SFMC_IF.finditer(html):
        var, op, val = _parse_sfmc_condition(m.group(1))
        conditionals.append(
            ConditionalToken(
                variable=var,
                operator=op,
                value=val,
                body_html=m.group(2),
                else_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )

    return TokenIR(variables=tuple(variables), conditionals=tuple(conditionals), loops=())


# ── Adobe Campaign (JSSP) ──

_ADOBE_OUTPUT: Final = re.compile(r"<%=\s*(\w[\w.]*)\s*%>")
_ADOBE_IF: Final = re.compile(
    r"<%\s*if\s*\((.+?)\)\s*\{%>([\s\S]*?)(?:<%\s*\}\s*else\s*\{%>([\s\S]*?))?<%\s*\}\s*%>"
)


def parse_adobe(html: str) -> TokenIR:
    variables: list[VariableToken] = []
    conditionals: list[ConditionalToken] = []

    for m in _ADOBE_OUTPUT.finditer(html):
        variables.append(
            VariableToken(
                name=m.group(1),
                filters=(),
                fallback=None,
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )

    for m in _ADOBE_IF.finditer(html):
        cond = m.group(1).strip()
        var, op, val = _parse_liquid_condition(cond)
        conditionals.append(
            ConditionalToken(
                variable=var,
                operator=op,
                value=val,
                body_html=m.group(2),
                else_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )

    return TokenIR(variables=tuple(variables), conditionals=tuple(conditionals), loops=())


# ── Mailchimp (Merge Tags) ──

_MC_OUTPUT: Final = re.compile(r"\*\|(\w+)\|\*")
_MC_IF: Final = re.compile(r"\*\|IF:(\w+)\|\*([\s\S]*?)(?:\*\|ELSE:\|\*([\s\S]*?))?\*\|END:IF\|\*")


def parse_mailchimp(html: str) -> TokenIR:
    variables: list[VariableToken] = []
    conditionals: list[ConditionalToken] = []
    consumed: set[tuple[int, int]] = set()

    for m in _MC_IF.finditer(html):
        conditionals.append(
            ConditionalToken(
                variable=m.group(1),
                operator="exists",
                value=None,
                body_html=m.group(2),
                else_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    for m in _MC_OUTPUT.finditer(html):
        if any(s <= m.start() and m.end() <= e for s, e in consumed):
            continue
        # Skip control merge tags
        tag = m.group(1)
        if tag in ("IF", "ELSE", "END", "ELSEIF"):
            continue
        variables.append(
            VariableToken(
                name=tag.lower(),
                filters=(),
                fallback=None,
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )

    return TokenIR(variables=tuple(variables), conditionals=tuple(conditionals), loops=())


# ── Iterable / SendGrid (Handlebars) ──

_HBS_VAR: Final = re.compile(r"\{\{(?!#|/)(\s*[\w.]+(?:\s+[\w.\"' ]+)*)\s*\}\}")
_HBS_IF: Final = re.compile(
    r"\{\{#if\s+([\w.]+)\s*\}\}([\s\S]*?)(?:\{\{else\}\}([\s\S]*?))?\{\{/if\}\}"
)
_HBS_EACH: Final = re.compile(r"\{\{#each\s+([\w.]+)\s*\}\}([\s\S]*?)\{\{/each\}\}")
_HBS_DEFAULT: Final = re.compile(r"\{\{defaultIfEmpty\s+([\w.]+)\s+['\"]([^'\"]*)['\"].*?\}\}")


def parse_iterable(html: str) -> TokenIR:
    variables: list[VariableToken] = []
    conditionals: list[ConditionalToken] = []
    loops: list[LoopToken] = []
    consumed: set[tuple[int, int]] = set()

    for m in _HBS_IF.finditer(html):
        conditionals.append(
            ConditionalToken(
                variable=m.group(1),
                operator="exists",
                value=None,
                body_html=m.group(2),
                else_html=m.group(3),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    for m in _HBS_EACH.finditer(html):
        loops.append(
            LoopToken(
                item_name="this",
                collection=m.group(1),
                body_html=m.group(2),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    # defaultIfEmpty helper → variable with fallback
    for m in _HBS_DEFAULT.finditer(html):
        if any(s <= m.start() and m.end() <= e for s, e in consumed):
            continue
        variables.append(
            VariableToken(
                name=m.group(1),
                filters=(FilterExpr(name="default", args=(m.group(2),)),),
                fallback=m.group(2),
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )
        consumed.add((m.start(), m.end()))

    for m in _HBS_VAR.finditer(html):
        if any(s <= m.start() and m.end() <= e for s, e in consumed):
            continue
        name = m.group(1).strip()
        if not name or name.startswith(("#", "/")):
            continue
        variables.append(
            VariableToken(
                name=name,
                filters=(),
                fallback=None,
                source_syntax=m.group(0),
                source_span=(m.start(), m.end()),
            )
        )

    return TokenIR(
        variables=tuple(variables),
        conditionals=tuple(conditionals),
        loops=tuple(loops),
    )


parse_sendgrid = parse_iterable


# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------

_ParseFn = Callable[[str], TokenIR]
_VarEmitFn = Callable[[VariableToken, list[str]], str]
_CondEmitFn = Callable[[ConditionalToken], str]
_LoopEmitFn = Callable[[LoopToken], str]
_EmitFn = Callable[[TokenIR, str], tuple[str, list[str]]]

_PARSER_REGISTRY: Final[dict[str, _ParseFn]] = {
    "braze": parse_braze,
    "sfmc": parse_sfmc,
    "klaviyo": parse_klaviyo,
    "hubspot": parse_hubspot,
    "mailchimp": parse_mailchimp,
    "iterable": parse_iterable,
    "sendgrid": parse_sendgrid,
    "activecampaign": parse_activecampaign,
    "brevo": parse_brevo,
    "adobe_campaign": parse_adobe,
}


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def _emit_liquid_var(v: VariableToken, prefix: str = "") -> str:
    """Emit a Liquid/Django/HubL variable token."""
    parts = [f"{prefix}{v.name}"]
    for f in v.filters:
        parts.append(_emit_liquid_filter(f))
    return "{{ " + " | ".join(parts) + " }}"


def _emit_liquid_filter(f: FilterExpr) -> str:
    reverse = {
        "default": "default",
        "uppercase": "upcase",
        "lowercase": "downcase",
        "date": "date",
        "truncate": "truncate",
        "capitalize": "capitalize",
        "strip": "strip",
        "escape": "escape",
        "url_encode": "url_encode",
    }
    name = reverse.get(f.name, f.name)
    if f.args:
        return f'{name}: "{f.args[0]}"'
    return name


def _emit_braze_token(v: VariableToken, _w: list[str]) -> str:
    return _emit_liquid_var(v)


def _emit_klaviyo_token(v: VariableToken, _w: list[str]) -> str:
    parts = [f"person.{v.name}"]
    for f in v.filters:
        fname = {
            "default": "default",
            "uppercase": "upper",
            "lowercase": "lower",
            "date": "date",
            "truncate": "truncatechars",
        }.get(f.name, f.name)
        if f.args:
            parts.append(f'{fname}: "{f.args[0]}"')
        else:
            parts.append(fname)
    return "{{ " + " | ".join(parts) + " }}"


def _emit_hubspot_token(v: VariableToken, _w: list[str]) -> str:
    parts = [f"contact.{v.name}"]
    for f in v.filters:
        fname = {
            "default": "default",
            "uppercase": "upper",
            "lowercase": "lower",
            "date": "datetimeformat",
            "truncate": "truncate",
        }.get(f.name, f.name)
        if f.args:
            parts.append(f'{fname}("{f.args[0]}")')
        else:
            parts.append(fname)
    return "{{ " + " | ".join(parts) + " }}"


def _emit_sfmc_token(v: VariableToken, warnings: list[str]) -> str:
    base = f"%%=v(@{v.name})=%%"
    if v.fallback:
        return f'%%=IIF(Empty(@{v.name}),"{v.fallback}",v(@{v.name}))=%%'
    for f in v.filters:
        if f.name == "uppercase":
            return f"%%=Uppercase(v(@{v.name}))=%%"
        if f.name == "lowercase":
            return f"%%=Lowercase(v(@{v.name}))=%%"
        if f.name == "truncate" and f.args:
            return f"%%=Substring(v(@{v.name}),1,{f.args[0]})=%%"
        if f.name == "date" and f.args:
            return f'%%=Format(@{v.name},"{f.args[0]}")=%%'
        if f.name != "default":
            warnings.append(f"Filter '{f.name}' not supported on sfmc")
    return base


def _emit_mailchimp_token(v: VariableToken, warnings: list[str]) -> str:
    for f in v.filters:
        if f.name != "default":
            warnings.append(f"Filter '{f.name}' not supported on mailchimp")
    return f"*|{v.name.upper()}|*"


def _emit_iterable_token(v: VariableToken, warnings: list[str]) -> str:
    if v.fallback:
        return f'{{{{defaultIfEmpty {v.name} "{v.fallback}"}}}}'
    for f in v.filters:
        if f.name == "default" and f.args:
            return f'{{{{defaultIfEmpty {v.name} "{f.args[0]}"}}}}'
        if f.name != "default":
            warnings.append(f"Filter '{f.name}' not supported on iterable")
    return "{{" + v.name + "}}"


def _emit_adobe_token(v: VariableToken, warnings: list[str]) -> str:
    for f in v.filters:
        if f.name != "default":
            warnings.append(f"Filter '{f.name}' not supported on adobe_campaign")
    return f"<%= {v.name} %>"


def _emit_activecampaign_token(v: VariableToken, _w: list[str]) -> str:
    return _emit_liquid_var(v, prefix="%")


def _emit_brevo_token(v: VariableToken, _w: list[str]) -> str:
    return _emit_liquid_var(v, prefix="contact.")


# ── Conditional emitters ──


def _emit_liquid_conditional(c: ConditionalToken, prefix: str = "") -> str:
    var = f"{prefix}{c.variable}"
    if c.operator == "exists":
        cond = var
    elif c.operator == "eq":
        cond = f'{var} == "{c.value}"'
    elif c.operator == "neq":
        cond = f'{var} != "{c.value}"'
    elif c.operator == "gt":
        cond = f"{var} > {c.value}"
    elif c.operator == "lt":
        cond = f"{var} < {c.value}"
    elif c.operator == "contains":
        cond = f'{var} contains "{c.value}"'
    else:
        cond = var
    result = f"{{% if {cond} %}}{c.body_html}"
    if c.else_html is not None:
        result += f"{{% else %}}{c.else_html}"
    result += "{% endif %}"
    return result


def _emit_sfmc_conditional(c: ConditionalToken) -> str:
    var = f"@{c.variable}"
    if c.operator == "exists":
        cond = f"NOT Empty({var})"
    elif c.operator == "eq":
        cond = f'{var} == "{c.value}"'
    elif c.operator == "neq":
        cond = f'{var} <> "{c.value}"'
    else:
        cond = f"NOT Empty({var})"
    result = f"%%[IF {cond} THEN]%%{c.body_html}"
    if c.else_html is not None:
        result += f"%%[ELSE]%%{c.else_html}"
    result += "%%[ENDIF]%%"
    return result


def _emit_mailchimp_conditional(c: ConditionalToken) -> str:
    result = f"*|IF:{c.variable.upper()}|*{c.body_html}"
    if c.else_html is not None:
        result += f"*|ELSE:|*{c.else_html}"
    result += "*|END:IF|*"
    return result


def _emit_hbs_conditional(c: ConditionalToken) -> str:
    result = f"{{{{#if {c.variable}}}}}{c.body_html}"
    if c.else_html is not None:
        result += f"{{{{else}}}}{c.else_html}"
    result += "{{/if}}"
    return result


def _emit_adobe_conditional(c: ConditionalToken) -> str:
    if c.operator == "exists":
        cond = c.variable
    elif c.operator == "eq":
        cond = f'{c.variable} == "{c.value}"'
    elif c.operator == "neq":
        cond = f'{c.variable} != "{c.value}"'
    else:
        cond = c.variable
    result = f"<% if ({cond}) {{%>{c.body_html}"
    if c.else_html is not None:
        result += f"<% }} else {{%>{c.else_html}"
    result += "<% } %>"
    return result


# ── Loop emitters ──


def _emit_liquid_loop(lp: LoopToken, prefix: str = "") -> str:
    return f"{{% for {lp.item_name} in {prefix}{lp.collection} %}}{lp.body_html}{{% endfor %}}"


def _emit_hbs_loop(lp: LoopToken) -> str:
    return f"{{{{#each {lp.collection}}}}}{lp.body_html}{{{{/each}}}}"


def _emit_sfmc_loop(lp: LoopToken) -> str:
    return f"<!-- MANUAL: Loop over {lp.collection} not directly supported in AMPscript -->"


# ── Full emitters combining variable + conditional + loop ──

_VAR_EMITTERS: Final[dict[str, _VarEmitFn]] = {
    "braze": _emit_braze_token,
    "sfmc": _emit_sfmc_token,
    "klaviyo": _emit_klaviyo_token,
    "hubspot": _emit_hubspot_token,
    "mailchimp": _emit_mailchimp_token,
    "iterable": _emit_iterable_token,
    "sendgrid": _emit_iterable_token,
    "activecampaign": _emit_activecampaign_token,
    "brevo": _emit_brevo_token,
    "adobe_campaign": _emit_adobe_token,
}


def _build_replacements(
    ir: TokenIR,
    warnings: list[str],
    var_emitter: _VarEmitFn,
    target: str,
) -> list[tuple[int, int, str]]:
    """Build (start, end, replacement) list from IR."""
    replacements: list[tuple[int, int, str]] = []

    for v in ir.variables:
        new_text = var_emitter(v, warnings)
        replacements.append((v.source_span[0], v.source_span[1], new_text))

    cond_emitter = _COND_EMITTERS.get(target)
    if cond_emitter:
        for c in ir.conditionals:
            new_text = cond_emitter(c)
            replacements.append((c.source_span[0], c.source_span[1], new_text))

    loop_emitter = _LOOP_EMITTERS.get(target)
    if loop_emitter:
        for lp in ir.loops:
            new_text = loop_emitter(lp)
            replacements.append((lp.source_span[0], lp.source_span[1], new_text))

    return replacements


def _apply_replacements(html: str, replacements: list[tuple[int, int, str]]) -> str:
    """Apply replacements right-to-left to preserve earlier offsets."""
    for start, end, text in sorted(replacements, key=lambda r: r[0], reverse=True):
        html = html[:start] + text + html[end:]
    return html


_COND_EMITTERS: Final[dict[str, _CondEmitFn]] = {
    "braze": lambda c: _emit_liquid_conditional(c),
    "sfmc": _emit_sfmc_conditional,
    "klaviyo": lambda c: _emit_liquid_conditional(c, "person."),
    "hubspot": lambda c: _emit_liquid_conditional(c, "contact."),
    "mailchimp": _emit_mailchimp_conditional,
    "iterable": _emit_hbs_conditional,
    "sendgrid": _emit_hbs_conditional,
    "activecampaign": lambda c: _emit_liquid_conditional(c, "%"),
    "brevo": lambda c: _emit_liquid_conditional(c, "contact."),
    "adobe_campaign": _emit_adobe_conditional,
}

_LOOP_EMITTERS: Final[dict[str, _LoopEmitFn]] = {
    "braze": lambda lp: _emit_liquid_loop(lp),
    "sfmc": _emit_sfmc_loop,
    "klaviyo": lambda lp: _emit_liquid_loop(lp, "person."),
    "hubspot": lambda lp: _emit_liquid_loop(lp, "contact."),
    "iterable": _emit_hbs_loop,
    "sendgrid": _emit_hbs_loop,
    "activecampaign": lambda lp: _emit_liquid_loop(lp, "%"),
    "brevo": lambda lp: _emit_liquid_loop(lp, "contact."),
    "adobe_campaign": lambda _lp: "<!-- MANUAL: Loop not supported in Adobe JSSP -->",
    "mailchimp": lambda _lp: "<!-- MANUAL: Loop not supported in Mailchimp merge tags -->",
}


def _make_emitter(target: str) -> _EmitFn:
    """Build a full emitter function for a target ESP."""
    var_emitter = _VAR_EMITTERS.get(target)
    if var_emitter is None:
        msg = f"No emitter for target ESP: {target}"
        raise DomainValidationError(msg)

    def emitter(ir: TokenIR, html: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        replacements = _build_replacements(ir, warnings, var_emitter, target)
        return _apply_replacements(html, replacements), warnings

    return emitter


_EMITTER_REGISTRY: Final[dict[str, _EmitFn]] = {esp: _make_emitter(esp) for esp in ALL_PLATFORMS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Map validator's ESPPlatform enum values to our Literal values
_VALIDATOR_TO_IR: Final[dict[str, str]] = {
    "braze": "braze",
    "sfmc": "sfmc",
    "adobe": "adobe_campaign",
    "klaviyo": "klaviyo",
    "mailchimp": "mailchimp",
    "hubspot": "hubspot",
    "iterable": "iterable",
}


def parse_tokens(html: str, platform: ESPPlatform) -> TokenIR:
    """Parse ESP-specific tokens from HTML into IR."""
    parser = _PARSER_REGISTRY.get(platform)
    if parser is None:
        msg = f"No parser for platform: {platform}"
        raise DomainValidationError(msg)
    result = parser(html)
    logger.info(
        "connectors.token_ir.parse_completed",
        platform=platform,
        variables=len(result.variables),
        conditionals=len(result.conditionals),
        loops=len(result.loops),
    )
    return result


def emit_tokens(ir: TokenIR, html: str, target: ESPPlatform) -> tuple[str, list[str]]:
    """Replace IR spans in HTML with target ESP syntax. Returns (html, warnings)."""
    emitter = _EMITTER_REGISTRY.get(target)
    if emitter is None:
        msg = f"No emitter for target: {target}"
        raise DomainValidationError(msg)
    result_html, warnings = emitter(ir, html)
    logger.info(
        "connectors.token_ir.emit_completed",
        target=target,
        warnings_count=len(warnings),
    )
    return result_html, warnings


def detect_and_parse(html: str) -> tuple[TokenIR, ESPPlatform]:
    """Auto-detect platform, then parse. Raises ValueError if no ESP detected."""
    detected, _confidence = _detect_platform(html)
    platform_str = str(detected.value)

    # Map from validator enum to our platform literal
    ir_platform = _VALIDATOR_TO_IR.get(platform_str)
    if ir_platform is None or platform_str == "unknown":
        msg = "Could not detect ESP platform from HTML content"
        raise DomainValidationError(msg)

    platform = cast(ESPPlatform, ir_platform)
    ir = parse_tokens(html, platform)
    return ir, platform
