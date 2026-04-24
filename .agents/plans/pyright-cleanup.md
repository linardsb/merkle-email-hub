# Pyright Strict Cleanup (735 errors → 0)

**Status:** baseline captured 2026-04-24 after commit `9623014`
**Goal:** `uv run pyright app/` returns `0 errors` so the `Backend > Type check (pyright)` CI step passes.
**Branch strategy:** work on `main` in a fresh session; commit per-phase (see Commits section).
**Estimated effort:** 3–5 hours of mechanical work. Don't let a long session accumulate — compact or rotate tabs at natural phase boundaries.

## Why this plan exists

Mypy went from 128→0 in commits `5cc3f4e`/`6edffbc`/`9623014`. Pyright (configured `typeCheckingMode = "strict"` in `pyproject.toml`) now surfaces as the only remaining code gate on both main and every Dependabot PR (~20 stuck PRs). This plan is the mechanical cleanup path the user chose after considering a soft-fail alternative.

The baseline is persisted at `.agents/plans/pyright-baseline.log` so you can cross-check that the numbers below still match reality before you start.

## Ground rules

1. **Re-run pyright first**, don't trust the numbers in this plan blindly:
   ```bash
   uv run pyright app/ > /tmp/pyright-current.log 2>&1
   tail -1 /tmp/pyright-current.log
   ```
   If the total drifts by more than ~20, re-read the Scope table.

2. **Don't fix with `# pyright: ignore[...]` unless the alternative is an invasive rewrite.** The user chose faithful B, not B-lite. Reserve ignores for:
   - Test files testing deliberately-broken code (e.g. `test_connector_wiring.py` — see Gotchas)
   - Lines where the type is genuinely `Any` from a third-party (YAML dicts, JSON responses) and casting doesn't carry its weight

3. **`# mypy: ignore-errors` does NOT suppress pyright.** The equivalent is either `# pyright: strict=false` at file top or `# pyright: ignore[<codes>]` per line.

4. **Don't touch runtime behaviour.** Every change should be annotation-only or a `cast(...)` insertion. If a fix requires changing what the code does, stop and flag it.

5. **Verify after every file or tight batch:**
   ```bash
   uv run pyright app/path/to/file.py 2>&1 | tail -3
   uv run pytest app/path/to/tests/ 2>&1 | tail -3  # if touched
   ```

6. **Commit in small batches** (per-file or per-category) so reverting a bad edit is cheap. See Commits section.

## Scope (at baseline capture)

**Total: 735 errors across 128 files.**

By error code (175 tagged; 560 are `"Type of X is partially unknown"` with no rule code):

| Code | Count | Typical fix |
|---|---|---|
| `reportUnknownVariableType` | 54 | Annotate the variable: `x: dict[str, Any] = ...` |
| `reportUntypedFunctionDecorator` | 40 | Add `# type: ignore[misc]` OR `cast(...)` the decorated function (slowapi `@limiter.limit(...)` is the main culprit) |
| `reportUnknownMemberType` | 34 | Annotate the container whose member is accessed |
| `reportUnusedImport` | 16 | Delete the import |
| `reportUnnecessaryIsInstance` | 14 | Delete the `isinstance(...)` branch (unreachable) |
| `reportUnnecessaryComparison` | 7 | Delete the comparison (always True/False) |
| `reportPossiblyUnboundVariable` | 4 | **Real bugs** — initialize var before all branches |
| `reportCallIssue` | 4 | Usually a real type mismatch, investigate |
| `reportOptionalSubscript` | 1 | Add `None` check before subscript |
| `reportConstantRedefinition` | 1 | Rename or use different name |
| `reportAssignmentType` | 1 | Fix the type, or `cast(...)` |

Top 20 files (covering ~450 of 735 errors):

| Count | File | Notes |
|---|---|---|
| 64 | `app/design_sync/service.py` | Untyped `client_hints`, `p.get()` dicts throughout |
| 45 | `app/design_sync/converter_service.py` | Same dict-get pattern |
| 40 | `app/design_sync/penpot/service.py` | JSON response parsing |
| 31 | `app/design_sync/figma/service.py` | `_fetch_variables`, JSON walking |
| 26 | `app/plugins/tests/test_connector_wiring.py` | **See Gotchas** — needs pyright-specific suppression |
| 24 | `app/ai/voice/transcriber.py` | 3rd-party API responses |
| 22 | `app/design_sync/tests/test_email_design_document.py` | Test fixtures |
| 19 | `app/knowledge/client_matrix.py` | |
| 19 | `app/ai/pipeline/registry.py` | YAML loader returns |
| 16 | `app/plugins/routes.py` | slowapi decorators likely dominant |
| 14 | `app/ai/prompt_store_routes.py` | slowapi decorators likely dominant |
| 13 | `app/ai/blueprints/nodes/qa_gate_node.py` | |
| 12 | `app/workflows/routes.py` | slowapi decorators likely dominant |
| 12 | `app/reporting/tests/test_report_builder.py` | |
| 12 | `app/ai/confidence_calibration.py` | |
| 11 | `app/knowledge/ontology/registry.py` | |
| 10 | `app/templates/upload/analyzer.py` | |
| 10 | `app/scheduling/routes.py` | slowapi decorators likely dominant |
| 10 | `app/ai/tests/test_confidence_calibration.py` | |
| 10 | `app/ai/pipeline/tests/test_adapters.py` | |

Files with 1–9 errors: 108 files, ~285 errors total. Handle last as a mop-up.

## Phases

### Phase 1 — Genuine bugs (4 errors, ~15 min)

**Targets:** `reportPossiblyUnboundVariable` (4), `reportOptionalSubscript` (1), `reportCallIssue` (4)

These are the only errors that could represent actual runtime bugs. Fix carefully, add tests if behaviour matters. Known one:
- `app/ai/adapters/openai_compat.py:342` — `json` possibly unbound

Command to list them:
```bash
grep -E "possibly unbound|Optional|reportCallIssue" /tmp/pyright-current.log
```

**Commit:** `fix(ai): resolve pyright-flagged possibly-unbound and call-issue bugs`

### Phase 2 — Trivial mechanical (37 errors, ~20 min)

**Targets:** `reportUnusedImport` (16), `reportUnnecessaryIsInstance` (14), `reportUnnecessaryComparison` (7)

Rules:
- Unused import: delete the import (check it's not re-exported via `__all__` first)
- Unnecessary isinstance: remove the branch (the isinstance always returns True, so the branch is always taken — inline the body)
- Unnecessary comparison: remove the comparison (result is constant)

Command to list them:
```bash
grep -E "reportUnusedImport|reportUnnecessaryIsInstance|reportUnnecessaryComparison" /tmp/pyright-current.log
```

**Commit:** `refactor: drop unused imports and dead isinstance/comparison branches`

### Phase 3 — slowapi decorator pattern (40 errors, ~30 min)

**Targets:** `reportUntypedFunctionDecorator`

The vast majority are `@limiter.limit("5/minute")` from `slowapi`. slowapi ships partial types that pyright-strict rejects. Files to hit:
- `app/plugins/routes.py`, `app/ai/prompt_store_routes.py`, `app/workflows/routes.py`, `app/scheduling/routes.py`, `app/ai/skills/routes.py`, `app/reporting/routes.py`, `app/ai/agents/scaffolder/variant_routes.py`

Preferred fix (module-level):
```python
# pyright: reportUntypedFunctionDecorator=false
```
Add at file top. Scope is the whole file but only affects that one rule; other pyright checks still run.

Alternative (per-decorator, more invasive): wrap `limiter.limit` in a typed helper. **Don't bother unless you see a real type regression.**

**Commit per logical group of routes, e.g.:** `types: silence slowapi decorator noise in routes (pyright-strict)`

### Phase 4 — Tagged unknown-type errors (88 errors, ~45 min)

**Targets:** `reportUnknownVariableType` (54) + `reportUnknownMemberType` (34)

These point at specific lines where a name's type is inferred as `Unknown`. Pattern:
```python
raw = json.load(f)            # inferred as Any → partially unknown
value = raw.get("key")        # Unknown member type
```

Fix by annotating at the introduction site:
```python
raw: dict[str, Any] = json.load(f)
value = raw.get("key")  # now dict[str, Any].get → Any, which is fine
```

Group by file and apply per-file.

**Commit per file:** `types({module}): annotate unknown-type locals for pyright strict`

### Phase 5 — "Partially unknown" bulk (560 errors, ~90–120 min)

This is the big one. These are untagged errors — pyright doesn't assign them a rule code because they cascade from the unknowns fixed in Phase 4. **Expect many to disappear after Phase 4 lands.**

After finishing Phase 4:
```bash
uv run pyright app/ > /tmp/pyright-after-phase4.log 2>&1
tail -1 /tmp/pyright-after-phase4.log
```

If the total is now much lower (expected drop ~200–300 errors), re-scope Phase 5 against the new list.

For errors that survive, the pattern is almost always:
```python
items: list[dict[str, Any]] = [...]  # ← was missing annotation
for item in items:
    x = item.get("foo")  # previously "partially unknown"
```

Or for third-party call returns:
```python
from typing import cast
resp = cast(dict[str, Any], external_api.call())
```

**Anti-pattern to avoid:** blanket `# pyright: ignore[reportUnknownMemberType, ...]` at file-top for entire service files. The user chose faithful B; only use file-level ignores for the specific exceptions listed in Gotchas.

**Commit per file or tight cluster:** `types({module}): type internal dicts for pyright strict`

### Phase 6 — 1-offs (balance, ~30 min)

After phases 1–5, remaining errors should be <50 and scattered. Fix each in isolation. Watch for:
- `reportConstantRedefinition` (1) — rename
- `reportAssignmentType` (1) — fix or cast

### Phase 7 — Verify (~10 min)

1. `uv run pyright app/ 2>&1 | tail -1` → must report `0 errors`.
2. `uv run mypy app/ 2>&1 | tail -1` → must still report `Success: no issues found in 1322 source files`.
3. `make test` → run full backend suite, no regressions.
4. Push and watch CI for `Type check (pyright)` green.

## Gotchas

1. **`app/plugins/tests/test_connector_wiring.py`** — already has `# mypy: ignore-errors` from prior commit `5cc3f4e`. Pyright doesn't respect that directive. Add `# pyright: strict=false` at the top alongside it. The file also has `pytestmark = pytest.mark.skip(...)` — tests don't run, so deep annotation fixes are wasted effort. `# pyright: strict=false` removes all 26 errors in that file in one line. This is the one sanctioned file-level ignore.

2. **`app/design_sync/service.py:108`** — already has `# type: ignore[assignment]  # structural Protocol subtype` for `MockDesignSyncService`. Do not remove. Same idiom applies to Sketch/Canva/Penpot registration on lines 93–102 (added in commit `5cc3f4e`). If pyright flags these, use the pyright-specific suppression form.

3. **`uv run pyright` may emit errors from `app/design_sync/tests/test_vlm_section_classifier.py`, `test_vlm_classifier.py`, `test_visual_verify.py`**. Those files had `-> patch:` annotations replaced with `-> Any:` in commit `5cc3f4e`. If pyright newly complains, check whether it wants the import of `patch` removed.

4. **`test_connector_wiring.py` is aspirational code** (Phase 46.5 never landed the `PluginConnectorAPI` surface). Don't try to fix it by writing the missing production code — that's out of scope for a CI green-up.

5. **mypy must stay green throughout.** Run `uv run mypy app/` at least once per commit. Some "fixes" for pyright (casting, adding Any) can accidentally upset mypy's strict rules (e.g. `no-any-return`).

6. **Existing `.env` has `CREDENTIALS__ENABLED=true`.** This only affects SDK regen (commit `6edffbc` history). For pyright it doesn't matter — `uv run pyright app/` scans all source files regardless of feature flags. But be aware if something SDK-related surfaces.

## Commits

Aim for ~8–12 commits total. Each commit:
- Touches one phase (or one file within a large phase)
- Passes mypy + pyright on changed files before committing
- Uses the conventional format (`types:`, `fix:`, `refactor:`, `chore:`)
- Ends with the trailer:
  ```
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```

Suggested commit titles:
1. `fix(ai): resolve pyright-flagged possibly-unbound and call-issue bugs`
2. `refactor: drop unused imports and dead isinstance/comparison branches`
3. `types: silence slowapi decorator noise across route modules`
4. `types(design-sync): annotate unknown dicts in service.py`
5. `types(design-sync): annotate unknown dicts in converter_service.py`
6. `types(design-sync): annotate unknown dicts in penpot + figma services`
7. `types(ai): annotate pipeline/registry, voice/transcriber, blueprints`
8. `types(knowledge): annotate client_matrix, ontology/registry`
9. `types(tests): annotate test fixtures and helpers`
10. `types(plugins): suppress pyright on test_connector_wiring.py (pyright-specific)`
11. `types: mop up remaining pyright errors across <10-error files`
12. `chore: verify pyright strict green on app/`

## Session handoff tips

- If you hit 30+ minutes and are below Phase 3 completion, push what you have and rotate tabs. A fresh context will be more reliable for Phases 4–5.
- If you finish Phase 4 and the "partially unknown" bulk is much smaller than 560, great — update this plan's counts before handing off.
- If you finish a phase and want to push, **always** run `uv run mypy app/` first. Breaking mypy with a pyright fix would regress commit `5cc3f4e`.

## Out of scope

- Semgrep (soft-failed by commit `4af9a00` — admin action to enable code scanning in repo Settings).
- Dependency Graph uv resolver failure (cognee/gunicorn/pyjwt conflict — a real dep conflict, needs pyproject edit, not a type fix).
- 1450 pyright **warnings** (mostly `reportPrivateUsage`, `reportUnusedFunction`) — warnings don't fail CI.
- The ~20 open Dependabot PRs — will auto-rebase and go green once main is green + commit-message-lint fix (commit pending) lands.
