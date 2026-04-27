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
    section_map: Mapping[int, "EmailSection"]
    button_ids: tuple[str, ...]
    text_meta: Mapping[int, "TextMeta"]
    gradients_map: Mapping[str, str]
    container_width: int
    parent_bg: str | None = None
    parent_font: str | None = None
    current_section: "EmailSection | None" = None
    depth: int = 0
    slot_counter: int = 0  # immutable; producers return new ctx with bumped counter

    def with_child(self, *, parent_bg=..., parent_font=..., section=...) -> "RenderContext":
        return replace(self, depth=self.depth + 1, ...)
```

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

`DesignSyncService` becomes a thin facade that holds references and delegates, OR is deleted entirely with each route depending on the specific carved service via DI.

### C3. Routes update

`app/design_sync/routes.py:1060` — currently 26 inline imports inside handlers. After carving, routes get specific service deps via FastAPI `Depends`. Route file shrinks.

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

### D2. Wait 2 weeks

In `traces/`, count `design_sync.converter.shim_called` events. If zero, proceed. If non-zero, identify the caller and migrate.

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

- [ ] **Part A**: `RenderContext` exists; `node_to_email_html` ≤ 30 LOC; per-node renderers ≤ 80 LOC each.
- [ ] **Part B**: `_convert_with_components` ≤ 30 LOC; 4 phase methods ≤ 80 LOC each.
- [ ] **Part C**: `DesignSyncService` carved into 6 services or facade-only; route file imports clean.
- [ ] **Part D1**: telemetry live for 2 weeks.
- [ ] **Part D3**: shims removed; ~750 LOC out.
- [ ] All snapshot/visual/data-regression tests green.
- [ ] PRs:
  - `refactor(design_sync): RenderContext + per-node dispatch (F010)`
  - `refactor(design_sync): split _convert_with_components into phases (F011)`
  - `refactor(design_sync): carve DesignSyncService (F012)`
  - `chore(design_sync): instrument legacy shims (F013 PR-1)`
  - `chore(design_sync): remove legacy shims after 2-week observation (F013 PR-2)`
- [ ] Mark F010, F011, F012, F013 as **RESOLVED**.
