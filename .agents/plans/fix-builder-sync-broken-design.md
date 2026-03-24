# Fix: Broken Builder Sync Design Preview

**Problem:** Imported/pasted HTML shows "Body content goes here." placeholders instead of actual section content in the visual builder preview.

**Root causes:** 2 bugs — one backend (section detection), one frontend (slot definition loss).

---

## Fix 1: Backend — XPath Too Restrictive in Section Analyzer

**File:** `app/templates/upload/analyzer.py:198`

**Bug:** `.//tr/td/table` only finds `<table>` elements that are direct children of `<td>`. Real email templates use intermediate `<div>` or `<center>` wrappers between `<td>` and section tables (confirmed in `email-templates/components/email-shell.html` and `cms/apps/web/e2e/fixtures/pre-compiled-email.html`).

**Fix:** Change to `.//tr/td//table` (descendant axis).

```python
# Before
inner_tables = wrapper.findall(".//tr/td/table")

# After
inner_tables = wrapper.findall(".//tr/td//table")
```

**Edge cases to verify:**
- Direct `tr > td > table` pattern still works (existing test)
- MSO ghost tables inside sections aren't misidentified as wrapper-level (existing test at line 311-340 — uses `sourceline` logic, independent of this XPath)
- No-wrapper templates (multiple top-level tables) still detected correctly
- Single table with no inner sections still falls through to single-section fallback

**New test cases needed:**
1. Wrapper with `<div style="max-width:600px">` between `<td>` and inner tables
2. Wrapper with `<center>` tag between `<td>` and inner tables
3. Wrapper with multiple levels of nesting (`div > section > div > table`)

**Effort:** Small — 1 line change + 3 test cases.

---

## Fix 2: Frontend — Slot Definitions Lost During Code→Builder Sync

**File:** `cms/apps/web/src/components/builder/visual-builder-panel.tsx:36`

**Bug:** `sectionNodeToBuilderSection()` hardcodes `slotDefinitions: []`. The HTML assembler in `use-builder.ts:298` loops over `slotDefinitions` to apply slot fills — with an empty array, the loop runs 0 times and placeholder text stays in the DOM.

**Root cause:** The palette drag path (`handleExternalDrop()`, line 193-242) fetches component versions from the API and extracts `slot_definitions`. The code→builder sync path skips this entirely.

**Data already available after parsing:**
- `componentId` (from `data-component-id` attribute)
- `slotValues` (from `data-slot-name` elements)
- `htmlFragment` (the raw section HTML)

**Data missing:**
- `slotDefinitions` (type, selector, required, placeholder, label)
- `defaultTokens`

### Implementation Steps

#### Step 2a: Prefetch component versions during sync

In `visual-builder-panel.tsx`, the sync effect (lines 131-141) receives `SectionNode[]` from the sync engine. Before converting to `BuilderSection[]`, prefetch any unknown component versions:

```typescript
// In the sync effect that receives syncedSections
const builderSections = await Promise.all(
  syncedSections.map(async (node) => {
    // Reuse existing fetchComponentHtml() + cache
    if (node.componentId > 0 && !htmlCacheRef.current.has(node.componentId)) {
      await fetchComponentHtml(node.componentId);
    }
    return sectionNodeToBuilderSection(node, htmlCacheRef.current);
  })
);
```

#### Step 2b: Wire slot definitions into conversion function

Update `sectionNodeToBuilderSection()` to accept and use the component cache:

```typescript
function sectionNodeToBuilderSection(
  node: SectionNode,
  versionCache: Map<number, VersionResponse>
): BuilderSection {
  const version = versionCache.get(node.componentId);
  const slotDefinitions: SlotDefinition[] = Array.isArray(version?.slot_definitions)
    ? version.slot_definitions
    : [];
  const defaultTokens = version?.default_tokens ?? null;

  return {
    // ... existing fields
    slotDefinitions,      // ← was []
    defaultTokens,        // ← was null
    slotFills: node.slotValues,
  };
}
```

#### Step 2c: Fallback for unknown components (componentId=0)

When HTML is imported without `data-component-id` annotations (Strategy 2 structural parse), `componentId` is 0. In this case, infer slot definitions from `data-slot-name` elements in the HTML fragment:

```typescript
function inferSlotDefinitions(htmlFragment: string, slotValues: Record<string, string>): SlotDefinition[] {
  // Parse htmlFragment, find elements with data-slot-name
  // Build minimal SlotDefinition with selector = [data-slot-name="X"]
  // This enables slot fill application even without API metadata
}
```

**Effort:** Medium — touches 3 functions in 1 file, needs the inference fallback for non-annotated HTML.

---

## Fix 3: Add Test Coverage for Both Paths

### Backend tests (`app/templates/upload/tests/test_analyzer.py`)

Add 3 new fixtures + assertions:

```python
WRAPPER_WITH_DIV_HTML = """<table width="600" align="center">
  <tr><td>
    <div style="max-width: 600px; margin: 0 auto;">
      <table><!-- section 1 --></table>
      <table><!-- section 2 --></table>
    </div>
  </td></tr>
</table>"""

WRAPPER_WITH_CENTER_HTML = """<table width="600" align="center">
  <tr><td>
    <center>
      <table><!-- section 1 --></table>
      <table><!-- section 2 --></table>
    </center>
  </td></tr>
</table>"""
```

Assert: `result.wrapper is not None`, `len(result.sections) >= 2`.

### Frontend tests (`cms/apps/web/src/components/builder/__tests__/`)

Add test for `sectionNodeToBuilderSection()`:
- With cached component version → slotDefinitions populated
- Without cache (componentId=0) → inferred from HTML
- Verify `processSection()` applies fills when slotDefinitions present

---

## Regarding Figma Sync for Testing

**No new Figma connection is needed.** The project has:

1. **Mock provider** (`app/design_sync/mock/service.py`) — simulates Figma/Penpot without external API calls. Create a connection with `provider="mock"` to test the full pipeline.

2. **Existing test fixtures** — `test_service.py`, `test_converter_integration.py`, `test_penpot_converter.py` cover the conversion pipeline with synthetic design data.

3. **The HTML upload path is separate** from design sync — the upload pipeline (`/api/v1/templates/upload`) processes raw HTML directly. The bugs are in the upload analyzer (XPath) and the frontend builder sync (slot definitions). Neither requires a Figma connection.

**To test end-to-end after fixes:**
- Upload an email HTML file via the Import HTML button
- Verify sections are correctly detected (backend fix)
- Verify preview shows actual content instead of placeholders (frontend fix)
- Alternatively: `make test` for backend + `make check-fe` for frontend unit tests

---

## Execution Order

1. **Fix 1** (backend XPath) — do first, simplest, unblocks section detection
2. **Fix 2a-2b** (frontend slot prefetch + wiring) — core fix for the preview
3. **Fix 2c** (fallback inference) — handles non-annotated HTML imports
4. **Fix 3** (tests) — verify both fixes, add regression coverage

**Total scope:** ~150 lines changed across 4 files + 2 test files.
