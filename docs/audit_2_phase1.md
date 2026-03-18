# Audit 2 — Phase 1: Critical & Blocking

**Depends on:** Nothing (run first)
**Gate:** `make check` must pass before proceeding to Phase 2

---

## 1.1 Alembic Duplicate Revision ID `a1b2c3d4e5f6`

**Problem:** Two migration files share the same revision ID and `down_revision`. Alembic cannot resolve the chain.

**Files:**
- `alembic/versions/a1b2c3d4e5f6_add_component_qa_result.py`
- `alembic/versions/a1b2c3d4e5f6_add_design_connections.py`

### Diagnosis commands

```bash
# Confirm the conflict
uv run alembic heads
uv run alembic history | head -40

# Check which was created first
ls -la alembic/versions/a1b2c3d4e5f6_*.py
git log --diff-filter=A --name-only -- 'alembic/versions/a1b2c3d4e5f6_*.py'
```

### Fix steps

1. Keep `a1b2c3d4e5f6` for whichever migration was committed first (check git log above)
2. Assign a new revision ID to the other file — e.g. `b2c3d4e5f6a7`
3. In the renamed file, update:
   - `revision = "b2c3d4e5f6a7"`
   - `down_revision = "a1b2c3d4e5f6"` (chains after the first one)
4. Find any downstream migration whose `down_revision` pointed at `a1b2c3d4e5f6` and update it to point at `b2c3d4e5f6a7` instead:
   ```bash
   grep -r 'down_revision.*a1b2c3d4e5f6' alembic/versions/ --include='*.py'
   ```
5. If the chain still has multiple heads after step 4, create a merge migration:
   ```bash
   uv run alembic merge heads -m "merge_component_qa_and_design_connections"
   ```

### Verification

```bash
uv run alembic heads          # Should show exactly 1 head
uv run alembic history        # Should show a single linear chain
uv run alembic upgrade head --sql  # Dry-run — should produce valid DDL
```

---

## 1.2 Blueprint Nodes: `model=` → `model_override=` Kwarg Fix

**Problem:** All blueprint nodes pass `model=model` to `provider.complete()`, but both providers read `kwargs.get("model_override", self._model)`. The `model=` kwarg is silently ignored — every node uses the default model regardless of tier.

### Diagnosis commands

```bash
# See all affected call sites
grep -rn 'provider\.complete\|provider\.stream' app/ai/blueprints/nodes/ --include='*.py'

# Confirm the provider expects model_override
grep -n 'model_override' app/ai/adapters/anthropic.py app/ai/adapters/openai_compat.py

# Confirm base agent does it correctly
grep -n 'model_override' app/ai/agents/base.py
```

### Fix steps

In every file under `app/ai/blueprints/nodes/`, replace `model=model` with `model_override=model` in all `provider.complete()` and `provider.stream()` calls:

```bash
# Files to edit (check each one):
app/ai/blueprints/nodes/scaffolder_node.py
app/ai/blueprints/nodes/dark_mode_node.py
app/ai/blueprints/nodes/outlook_fixer_node.py
app/ai/blueprints/nodes/accessibility_node.py
app/ai/blueprints/nodes/personalisation_node.py
app/ai/blueprints/nodes/code_reviewer_node.py
app/ai/blueprints/nodes/knowledge_node.py
app/ai/blueprints/nodes/innovation_node.py
app/ai/blueprints/nodes/visual_qa_node.py
```

For each file:
1. Open it, find every `provider.complete(messages, model=model)` or `provider.stream(messages, model=model)`
2. Change `model=model` to `model_override=model`
3. Do NOT change the variable name `model` itself — only the keyword argument name

### Verification

```bash
# Confirm no remaining wrong kwarg
grep -rn 'provider\.complete.*model=' app/ai/blueprints/nodes/ | grep -v 'model_override'
grep -rn 'provider\.stream.*model=' app/ai/blueprints/nodes/ | grep -v 'model_override'
# Both should return empty

# Run tests
make test
make eval-golden  # Confirms model routing works end-to-end
```

---

## Phase 1 Gate

```bash
make check   # lint + types + tests + security — must all pass
```

If `make check` passes, proceed to Phase 2.
