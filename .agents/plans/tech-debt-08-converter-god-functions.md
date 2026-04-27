# Tech Debt 08 — Decompose `design_sync` Converter God Functions

**Source:** `TECH_DEBT_AUDIT.md`
**Scope:** Three god functions and one god class in the design→email converter pipeline. Plus retiring two legacy converter shims via telemetry-then-remove.
**Goal:** `node_to_email_html` parameters bundled into `RenderContext`. `_convert_with_components` split into staged dataclass phases. `DesignSyncService` carved along boundary lines. Legacy shims instrumented and migrated.
**Estimated effort:** **2 sessions.** F013 (legacy shim retirement) requires 2 weeks of production telemetry between part C1 and part C3 — those steps live in different PRs.
**Prerequisite:** Plan 06 landed (reduces qa_engine surface). Plan 07 landed (engine decomposition is similar pattern, builds technique).

## Findings addressed

F010 (`node_to_email_html` 551 LOC, 16 params) — Critical
F011 (`_convert_with_components` 325 LOC) — Critical
F012 (`DesignSyncService` 49 methods, 1729 LOC) — Critical
F013 (legacy converter shims still wired) — Critical

## Pre-flight

```bash
git checkout -b refactor/tech-debt-08-converter-decomp
make check
```

Capture snapshot baselines for the converter:
```bash
make snapshot-test           # 3 active cases (MAAP/Starbucks/Mammut + REFRAME)
make snapshot-visual         # ODiff pixel diff
cp -r data/snapshot/baseline data/snapshot/baseline.before
```

The converter has visual regression tests. Use them as the safety net.

---

## Part A — `RenderContext` for `node_to_email_html` (F010)

### A1. Define the context dataclass

**New file:** `app/design_sync/render_context.py`:
```python
from dataclasses import dataclass, field, replace
from typing import Mapping

@dataclass(frozen=True)
class RenderContext:
    section_map: Mapping[str, "EmailSection"] = field(default_factory=dict)
    button_ids: frozenset[str] = field(default_factory=frozenset)
    text_meta: Mapping[str, "TextBlock"] = field(default_factory=dict)
    gradients_map: Mapping[str, "ExtractedGradient"] = field(default_factory=dict)
    props_map: Mapping[str, "_NodeProps"] = field(default_factory=dict)
    container_width: int = 600
    parent_bg: str | None = None
    parent_font: str | None = None
    current_section: "EmailSection | None" = None
    body_font_size: float = 16.0
    compat: "ConverterCompatibility | None" = None
    indent: int = 0
    depth: int = 0
    # Shared reference. Frozen dataclass forbids field reassignment, NOT
    # mutation of the dict's contents. _next_slot_name() mutates this in
    # place; with_child() preserves the reference via dataclasses.replace.
    _slot_counts: dict[str, int] = field(default_factory=dict)

    def with_child(
        self,
        *,
        parent_bg: str | None = None,
        parent_font: str | None = None,
        section: "EmailSection | None" = None,
    ) -> "RenderContext":
        return replace(
            self,
            depth=self.depth + 1,
            indent=self.indent + 1,
            parent_bg=parent_bg if parent_bg is not None else self.parent_bg,
            parent_font=parent_font if parent_font is not None else self.parent_font,
            current_section=section if section is not None else self.current_section,
        )

    @classmethod
    def from_legacy_kwargs(cls, **kw: object) -> "RenderContext":
        """Test/migration helper. Maps the pre-refactor kwargs to a RenderContext.
        Preserves shared-reference semantics for slot_counter (callers passing
        the same dict across multiple calls still see mutations propagate)."""
        slot_counts = kw.get("slot_counter")
        return cls(
            section_map=kw.get("section_map") or {},  # type: ignore[arg-type]
            button_ids=frozenset(kw.get("button_ids") or ()),  # type: ignore[arg-type]
            text_meta=kw.get("text_meta") or {},  # type: ignore[arg-type]
            gradients_map=kw.get("gradients_map") or {},  # type: ignore[arg-type]
            props_map=kw.get("props_map") or {},  # type: ignore[arg-type]
            container_width=kw.get("container_width", 600),  # type: ignore[arg-type]
            parent_bg=kw.get("parent_bg"),  # type: ignore[arg-type]
            parent_font=kw.get("parent_font"),  # type: ignore[arg-type]
            current_section=kw.get("current_section"),  # type: ignore[arg-type]
            body_font_size=kw.get("body_font_size", 16.0),  # type: ignore[arg-type]
            compat=kw.get("compat"),  # type: ignore[arg-type]
            indent=kw.get("indent", 0),  # type: ignore[arg-type]
            _slot_counts=slot_counts if isinstance(slot_counts, dict) else {},
        )
```

**Slot-counter ownership decision:** shared-reference object (the `_slot_counts` dict), not an immutable int threaded via return tuples. Renderers keep the `Callable[[DesignNode, RenderContext], str]` signature (no return-tuple plumbing). `_next_slot_name(ctx._slot_counts, slot_type)` mutates the dict in place; this preserves the existing `converter.py:403` helper unchanged.

### A2. Refactor `node_to_email_html`

`app/design_sync/converter.py:616-1166` — replace 16-param signature with `(node: DesignNode, ctx: RenderContext)`. Recursion calls become `node_to_email_html(child, ctx.with_child(...))`.

### A3. Extract per-node-type renderers

```python
NODE_RENDERERS: dict[NodeType, Callable[[DesignNode, RenderContext], str]] = {
    NodeType.TEXT:   _render_text_node,
    NodeType.FRAME:  _render_frame_node,
    NodeType.VECTOR: _render_vector_node,
    NodeType.IMAGE:  _render_image_node,
    NodeType.GROUP:  _render_group_node,
    NodeType.COMPONENT: _render_component_node,
}

def node_to_email_html(node, ctx) -> str:
    renderer = NODE_RENDERERS.get(node.type, _render_unknown_node)
    return renderer(node, ctx)
```

Each `_render_*_node` is independently testable and < 80 LOC.

### A4. Verify visual snapshots

`make snapshot-visual` against the saved baselines. Diff must be zero.

### A5. Migrate test callsites in same PR

The signature change breaks 14 test callsites that pass legacy kwargs. Migrate them via the `RenderContext.from_legacy_kwargs(...)` factory — do **not** add a backward-compat overload to `node_to_email_html` itself.

Affected files (pre-counted in preflight):
- `app/design_sync/tests/test_image_pipeline.py` — 9 sites, all `node_to_email_html(node)` (single positional). These pass through unchanged because `RenderContext()` defaults are valid; just confirm they still parse after the signature flip.
- `app/design_sync/tests/test_converter_fixes.py` — 5 sites passing `button_ids={"btn1"}`. Replace each with:
  ```python
  html = node_to_email_html(parent, RenderContext.from_legacy_kwargs(button_ids={"btn1"}))
  ```
- `app/design_sync/tests/test_builder_annotations.py` — 5 sites passing `slot_counter=counter` (and one with `button_ids` + `slot_counter`). Replace:
  ```python
  counter: dict[str, int] = {}
  result = node_to_email_html(node, RenderContext.from_legacy_kwargs(slot_counter=counter))
  # counter still mutated across calls — shared-reference semantics preserved
  ```

Verify after migration: `make test app/design_sync/tests/test_builder_annotations.py app/design_sync/tests/test_converter_fixes.py app/design_sync/tests/test_image_pipeline.py -v`.

---

## Part B — Split `_convert_with_components` (F011)

### B1. Define phase dataclasses

**New file:** `app/design_sync/conversion_phases.py`:
```python
@dataclass(frozen=True)
class MatchPhase:
    matches: list[ComponentMatch]
    group_map: dict[int, RepeatingGroup]
    sibling_groups: list[RepeatingGroup]

@dataclass(frozen=True)
class RenderPhase:
    html: str
    section_traces: list[SectionTrace]
    rendered_group_ids: set[int]

@dataclass(frozen=True)
class VerifyPhase:
    final_html: str
    fidelity: float
    corrections_applied: int
    iterations: int

@dataclass(frozen=True)
class CompilePhase:
    final_html: str
    contract_results: list[ContractResult]
```

### B2. Refactor `_convert_with_components`

`app/design_sync/converter_service.py:649-973` — the body becomes:
```python
async def _convert_with_components(self, structure, tokens, options) -> ConversionResult:
    match = await self._match_phase(structure, tokens, options)
    render = await self._render_phase(match, tokens, options)
    if options.verify_enabled:
        verify = await self._verify_phase(render, structure, options)
    else:
        verify = VerifyPhase.from_render(render)
    compile_ = await self._compile_phase(verify, options)
    return ConversionResult.from_phases(match, render, verify, compile_)
```

Each `_*_phase` is ≤ 80 LOC.

### B3. Per-phase tests

`app/design_sync/tests/test_conversion_phases.py` — one test class per phase, mocking the prior phase's output.

---

## Part C — `DesignSyncService` carve-out (F012)

### C1. Identify boundaries

`app/design_sync/service.py` already has section comments. Confirmed groups:
- Connections (sync, OAuth, status)
- Assets (download, manifest)
- Imports (HTML import, parse, mapping)
- Webhooks (Figma webhook, debounced sync)
- Tokens & structure (the core conversion bridge)
- Project access (RBAC for design connections)

### C2. Carve

```
app/design_sync/services/
  __init__.py
  connection_service.py   ← was: methods 1-12 of DesignSyncService
  assets_service.py       ← methods 13-18
  import_service.py       ← already exists at app/design_sync/import_service.py;
                            move ownership boundary or merge here
  webhook_service.py      ← methods 19-23
  conversion_service.py   ← methods 24-35 (the core that talks to converter_service)
  access_service.py       ← project-access checks (small)
```

**This PR: facade only.** `DesignSyncService` becomes a thin (~50 LOC) facade holding the 6 carved service refs and delegating each public method. **Do not delete the class in this PR** — ~30 test fixtures (`test_webhook.py`, `test_import_service.py`, `test_build_document.py`) instantiate `DesignSyncService(mock_db)` directly, plus MCP tools / blueprint engine / routes import it. Mass-migrating callers in the same PR balloons the diff and risks breaking unrelated paths.

A follow-up plan **`tech-debt-08b-design-sync-service-deletion.md`** must be opened before this PR merges. It tracks: (a) migrating each route handler in `routes.py` from facade → direct carved-service `Depends`, (b) migrating MCP tools and blueprint engine references, (c) updating test fixtures to mock the specific carved service, (d) deleting the facade. Reference 08b in the `Done when` checklist below.

### C3. Routes update

`app/design_sync/routes.py:1060` — currently 26 inline imports inside handlers. **In this PR**, routes still depend on `DesignSyncService` (the facade). Inline imports can be tidied opportunistically but the DI-per-carved-service migration lands in 08b. Route file shrinks materially only after 08b.

---

## Part D — Legacy shim retirement (F013)

**THIS SPANS TWO PRs** because of the telemetry window.

### D1. PR-1: Add telemetry

`app/design_sync/converter_service.py:441,505,1024` — at each shim entry, emit:
```python
logger.info("design_sync.converter.shim_called",
            entry=__name__, caller=inspect.stack()[1].function)
warnings.warn("convert_design/convert_layout shim is deprecated; use convert_document",
              DeprecationWarning, stacklevel=2)
```

Migrate the two known callers:
- `app/design_sync/service.py:362` → call `convert_document` directly.
- `app/design_sync/penpot/service.py:165` → same.

After the call-site migration, the only path that hits the shims is from external code (none expected).

### D2. Wait 2 weeks (calendar-tracked)

The window is non-negotiable — its purpose is to detect *unknown* external callers. Skipping = silent breakage risk for consumers we don't know about.

After D1 merges, append a tracking row to the active `TODO.md` "Operational follow-ups" section (or create one) with a target date 14 days out. Today is `2026-04-27`, so the row reads:

> **2026-05-11 — F013 D3 readiness check.** Run `grep -c design_sync.converter.shim_called traces/*.jsonl traces/structured.log 2>/dev/null` (and any centralised log store the team uses). If count is **zero**, proceed to D3. If **non-zero**, identify each caller from the `caller=` log field, migrate it to `convert_document`, and reset the timer to a fresh +14 days.

Do not take any code action on D3 in the same session as D1.

### D3. PR-2: Remove the shims

After 2 clean weeks:
- Delete `_convert_recursive` (`converter_service.py:1013-1156`) — only if it's not the MJML-failure fallback. **Verify**: the MJML fallback path is `:530` and is *separate* from the shim entries. Keep it.
- Delete the shim methods at `:441`, `:505`, `:1024`.
- Delete `node_to_email_html` from `app/design_sync/converter.py:616-1166` if `_convert_recursive` no longer needs it. ~750 LOC out.

### D4. Verify

```bash
make snapshot-visual
# All cases pass — the shims weren't doing anything different.
```

---

## Verification

```bash
make check
make test app/design_sync/ -v
make snapshot-test
make snapshot-visual         # zero pixel diff vs baseline.before
make converter-data-regression
```

## Rollback

Each part (A/B/C/D1/D3) is an independent revert. The most invasive is C — services carve-out. If carved services have import cycles, fold back into `service.py` and revisit boundaries.

## Risk notes

- **Part D requires calendar discipline.** The telemetry window is *real*. Don't skip to D3 because "no one is calling it" — verify with logs.
- **`node_to_email_html` is exported as a public symbol.** Other modules in `app/design_sync/` import its helpers (`_relative_luminance`, `_contrast_ratio`, etc. — see audit F024-F025). Extract those helpers to `app/shared/color.py` *before* deleting `converter.py`, otherwise imports break.
- **`DesignSyncService` is referenced from MCP tools, routes, blueprint engine.** A facade-then-direct-dep migration is safest: keep facade in place for one PR, migrate callers in a follow-up.
- **Snapshot tests are the safety net.** They've caught regressions in Phases 41, 47, 49. Trust them; if a snapshot diff appears, treat it as a bug.

## Done when

- [x] **Part A**: `RenderContext` exists; `node_to_email_html` ≤ 30 LOC; per-node renderers ≤ 80 LOC each; 49 test callsites migrated via `from_legacy_kwargs` (plan undercounted — actual count was 49 across 7 test files).
- [ ] **Part B**: `_convert_with_components` ≤ 30 LOC; 4 phase methods ≤ 80 LOC each.
- [ ] **Part C**: 6 carved services exist under `app/design_sync/services/`; `DesignSyncService` is a ≤50-LOC facade (NOT deleted); follow-up plan `tech-debt-08b-design-sync-service-deletion.md` created and linked here.
- [ ] **Part D1**: telemetry live; tracking row added to `TODO.md` with date `2026-05-11`.
- [ ] **Part D3**: deferred to a separate session after the telemetry window closes; do not attempt in this session.
- [ ] All snapshot/visual/data-regression tests green.
- [ ] PRs:
  - `refactor(design_sync): RenderContext + per-node dispatch (F010)`
  - `refactor(design_sync): split _convert_with_components into phases (F011)`
  - `refactor(design_sync): carve DesignSyncService (F012)`
  - `chore(design_sync): instrument legacy shims (F013 PR-1)`
  - `chore(design_sync): remove legacy shims after 2-week observation (F013 PR-2)`
- [ ] Mark F010, F011, F012, F013 as **RESOLVED**.
