# Audit 2 — Phase 4: Low Severity & Cleanup

**Depends on:** Phase 3 complete, `make check` + `make check-fe` passing
**Gate:** `make check` must pass with **0 type errors**

---

## 4.1 Test Type Errors (37 → 0 mypy errors)

### 4.1a Ontology Sync Tests — Method Assignment (15 errors)

**File:** `app/knowledge/ontology/sync/tests/test_service.py`

**Problem:** Direct method assignment (`service.method = AsyncMock(...)`) flagged by mypy `[method-assign]`.

### Diagnosis

```bash
grep -n 'method-assign' <(uv run mypy app/knowledge/ontology/sync/tests/test_service.py 2>&1)
```

### Fix

Replace direct method assignments with `unittest.mock.patch.object()`:

```python
# BEFORE:
service.fetch_data = AsyncMock(return_value=data)

# AFTER:
with patch.object(service, "fetch_data", new=AsyncMock(return_value=data)):
    result = await service.process()
```

Alternatively, if the tests use pytest, use `monkeypatch.setattr()`:
```python
monkeypatch.setattr(service, "fetch_data", AsyncMock(return_value=data))
```

Apply to all 15 occurrences (lines: 41, 42, 63, 64, 91, 103, 104, 114, 115, 136, 137, 196, 197, 225, 226).

---

### 4.1b Deliverability Tests — Missing Type Annotations (13 errors)

**File:** `app/qa_engine/tests/test_deliverability.py`

**Problem:** Test function parameters (fixtures) missing type annotations.

### Diagnosis

```bash
grep -n 'no-untyped-def' <(uv run mypy app/qa_engine/tests/test_deliverability.py 2>&1)
```

### Fix

Add type annotations to all test functions. Most will be `Any` for fixtures:

```python
# BEFORE:
def test_calculates_score(self, predictor):

# AFTER:
def test_calculates_score(self, predictor: Any) -> None:
```

Add `from typing import Any` if not imported. Apply to all 13 functions (lines: 65, 71, 77, 83, 89, 97, 108, 114, 120, 126, 133, 139, 148).

---

### 4.1c Prompt Store Test — Stale Type Ignore (1 error)

**File:** `app/ai/tests/test_prompt_store.py`

### Fix

Remove the unused `# type: ignore` comment at line 499.

```bash
grep -n 'type: ignore' app/ai/tests/test_prompt_store.py
```

Delete the comment.

---

### Verification

```bash
uv run mypy app/   # Should show 0 errors
make types         # Full type check pass
```

---

## 4.2 Unused/Stale Dependencies

**File:** `pyproject.toml`

### Fix

1. **Remove `pydub`** — unused (voice pipeline uses raw bytes):
   ```bash
   grep -rn 'pydub\|from pydub' app/ --include='*.py'
   # Should return nothing → safe to remove
   ```
   Delete `"pydub>=0.25.1"` from `[project.dependencies]`

2. **Add `pyyaml`** — used transitively but not declared:
   ```bash
   grep -rn 'import yaml' app/ --include='*.py'
   # Should show 5+ files
   ```
   Add `"pyyaml>=6.0"` to `[project.dependencies]`

3. **Remove stale mypy override** for `jose.*`:
   Delete the `[[tool.mypy.overrides]]` block for `module = "jose.*"`

4. **Re-lock:**
   ```bash
   uv lock
   ```

### Verification

```bash
uv sync && make test
```

---

## 4.3 `Number(params.id)` NaN Validation

**Files:**
- `cms/apps/web/src/app/projects/[id]/workspace/page.tsx`
- `cms/apps/web/src/app/(dashboard)/approvals/[id]/page.tsx`
- `cms/apps/web/src/app/(dashboard)/projects/[id]/brand/page.tsx`

### Fix

In each file, after `const projectId = Number(params.id)`, add:

```typescript
if (Number.isNaN(projectId)) {
  notFound();
}
```

Import `notFound` from `next/navigation` if not already imported.

### Verification

```bash
make check-fe
```

---

## 4.4 Hardcoded English DOMAIN_LABELS (i18n)

**Files (duplicated in 3 places):**
- `cms/apps/web/src/app/(dashboard)/knowledge/page.tsx`
- `cms/apps/web/src/components/knowledge/knowledge-search-result.tsx`
- `cms/apps/web/src/components/knowledge/knowledge-document-card.tsx`

### Fix

1. Add keys to all 6 locale files (`cms/apps/web/messages/{en,de,ar,es,fr,ja}.json`):
   ```json
   "knowledge": {
     "domainLabels": {
       "css_support": "CSS Support",
       "best_practices": "Best Practices",
       "client_quirks": "Client Quirks"
     }
   }
   ```
   Translate for non-English locales.

2. In each component, replace the hardcoded object:
   ```typescript
   // BEFORE:
   const DOMAIN_LABELS: Record<string, string> = {
     css_support: "CSS Support",
     best_practices: "Best Practices",
     client_quirks: "Client Quirks",
   };

   // AFTER:
   const t = useTranslations("knowledge");
   // Usage: t(`domainLabels.${domain}`)
   ```

3. **Deduplicate**: Remove the object from all 3 files — the translation hook replaces it.

### Verification

```bash
make check-fe
```

---

## 4.5 Makefile Cleanup

**File:** `Makefile`

### Fix

1. Find the `.PHONY` line and append the missing targets:
   ```makefile
   .PHONY: ... docker-logs test-properties e2e-ui sdk-local db-migrate db-revision eval-refresh help
   ```

2. Remove the `e2e-all` target (it's identical to `e2e`, already cleaned up in Phase 2)

### Verification

```bash
make help  # Should list all targets without error
```

---

## 4.6 Minor Frontend Issues

### 4.6a `useMemo` stale `docRef` in collaboration hook

**File:** `cms/apps/web/src/hooks/use-collaboration.ts:145-147`

**Fix:** Replace `useMemo` with `useState` + `useEffect` that updates `yText` when `docRef.current` changes:
```typescript
const [yText, setYText] = useState<Y.Text | null>(null);
// Inside the existing useEffect where doc is created:
setYText(doc.getText("content"));
```

### 4.6b Module-level `blockIdCounter`

**File:** `cms/apps/web/src/hooks/use-liquid-builder.ts:8`

**Fix:** Move inside the hook as a `useRef`:
```typescript
const blockIdCounter = useRef(1000);
// Usage: blockIdCounter.current++ instead of blockIdCounter++
```

### 4.6c `selectedNodeIdsRef` plain object

**File:** `cms/apps/web/src/components/design-sync/design-file-browser.tsx:208`

**Fix:**
```typescript
// BEFORE:
const selectedNodeIdsRef = { current: selectedNodeIds };

// AFTER:
const selectedNodeIdsRef = useRef(selectedNodeIds);
selectedNodeIdsRef.current = selectedNodeIds;
```

### 4.6d `handleEspExport` stale closure

**File:** `cms/apps/web/src/components/connectors/export-dialog.tsx:188`

**Fix:** Use a ref to always read latest `espStates`:
```typescript
const espStatesRef = useRef(espStates);
espStatesRef.current = espStates;
// In handleEspExport: read from espStatesRef.current instead of espStates
```

### 4.6e Visual QA stale `handleCapture`

**File:** `cms/apps/web/src/components/visual-qa/visual-qa-dialog.tsx:77-81`

**Fix:** Add `handleCapture` to the dependency array, or use a ref pattern.

### 4.6f `useDeleteVoiceBrief` null guard

**File:** `cms/apps/web/src/hooks/use-voice-briefs.ts:104`

**Fix:** Add early return:
```typescript
if (!projectId) return;
```

### 4.6g Approval page hardcoded "Build #"

**File:** `cms/apps/web/src/app/(dashboard)/approvals/[id]/page.tsx:102`

**Fix:** Use i18n:
```typescript
t("approvals.buildNumber", { id: approval.build_id })
```
Add the key to all 6 locale files.

### Verification

```bash
make check-fe
```

---

## Phase 4 Gate (Final)

```bash
make check      # 0 lint errors, 0 type errors, all tests pass
make check-fe   # frontend clean
```

After Phase 4 passes, the full audit is resolved. Delete `docs/audit_2.md` and the phase files if desired, or keep as reference.
