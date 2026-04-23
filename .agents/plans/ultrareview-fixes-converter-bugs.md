# Ultrareview Fixes — Converter Regression Bugs

**Source:** ultrareview session `01RK1iqSnsaJfpqkdBHSEVex` against `main` (2026-04-23).

3 normal-severity bugs, all introduced alongside recent design_sync converter work (social icon extraction, CTA token overrides, training-case endpoint). Each is a small, mechanical fix. No architecture change.

## Summary

| # | Bug | Scope | Files touched |
|---|-----|-------|---------------|
| 1 | `ButtonElement.icon_url` stores a Figma node ID, not a URL → broken `<img src="2833:1172">` in social sections | bug_003 | `figma/layout_analyzer.py`, `component_matcher.py`, `tests/test_cta_fidelity.py` |
| 2 | `_cta` token overrides use document-wide regexes → outer card `border-radius`/`border-color`/`background-color` clobbered by inner button's values | bug_006 | `component_renderer.py`, new tests |
| 3 | `create_training_case` writes files before manifest duplicate check → stuck 409 state when manifest + dir are out of sync | bug_004 | `service.py`, `tests/test_routes_training_cases.py` |

## Research Summary

Parallel research (Explore agents) validated every file ref from the ultrareview output against `main` as of 2026-04-23. All line numbers below are verified present.

**Bug 1 — full blast radius of the `icon_url` → `icon_node_id` rename** (repo-wide grep, every site that must change):

| File | Lines | Kind |
|------|-------|------|
| `app/design_sync/figma/layout_analyzer.py` | 104, 1085 | field def + producer |
| `app/design_sync/component_matcher.py` | 1218 | `_fills_social` consumer |
| `app/design_sync/tests/test_cta_fidelity.py` | 105, 113, 117, 198, 207 | 5 test assertions |
| **Total** | **8 refs** | |

**Explicit non-matches — do NOT touch** (unrelated fields named `icon_url` on other Pydantic models):
- `app/ai/agents/scaffolder/assembler.py:470,478-479` — `_inject_social_links(self, html: str, social_links: tuple[SocialLink, ...])` iterates `for link in social_links` and reads `link.icon_url` where `link` is provably a `SocialLink` by the function signature. Researcher flagged as a possible miss; verified unrelated via direct read during planning.
- `app/projects/design_system.py:114,124,126` — `SocialLink.icon_url` field + validator (class defined at `design_system.py:98`; `LogoConfig` at `:68` has no `icon_url` field).
- `app/seed_demo.py:65-66` — `SocialLink` dict literal.
- `app/components/data/component_manifest.yaml:485,487` — YAML slot name.
- `app/design_sync/email_design_document.py:710, 758` constructs `ButtonElement` but **without** `icon_url=` kwarg — safe. Same for `test_mjml_generator.py:222,449,468`, `test_component_matcher.py:78,603,761`, `test_convert_document.py:406`, `test_mjml_templates.py:109`.

Precedent naming (`ImagePlaceholder.export_node_id`) exists at `figma/layout_analyzer.py:87` — the rename aligns with the existing convention.

**Bug 2 — CTA scoping verification:**
- Unscoped dispatch at `component_renderer.py:557-571`: confirmed. All 4 unscoped `_replace_css_prop_all` calls present.
- Existing scoped helper pattern (`_CTA_LINK_COLOR_RE` + `_replace_cta_text_color`): present at `component_renderer.py:639-653`. New helpers follow this shape.
- `_replace_css_prop_all` at 634, `_update_vml_arcsize` at 657.
- **Template attribute ordering** (`class="cta-btn|cta-ghost"` appears before `style="..."` within the same opening tag): verified across all 150 component templates via `rg`. No template reorders. Similarly for `data-slot="cta_url"` on inline anchors in card templates.
- VML roundrect distribution: only `email-templates/components/cta-button.html` emits `<v:roundrect>` among the production components (button-filled.html / button-ghost.html use CSS `border-radius` on the fallback table, not VML). The 5 golden-reference fixtures under `email-templates/components/golden-references/` also contain VML but those are reference snapshots, not rendered components.

**Bug 3 — training case ordering verification:**
- `create_training_case` at `service.py:1808-1895` — ordering confirmed (validate → `case_dir.exists()` check → mkdir at 1837 → write expected.html at 1840 → optional screenshot at 1845-1848 → manifest read + dup check at 1862-1868 → raise). Mkdir precedes manifest check — the bug.
- Route handler: `routes.py:1028-1029` maps `TrainingCaseExistsError` → 409.
- Exceptions: `TrainingCaseError` (base) at `exceptions.py:66`, `TrainingCaseExistsError` (subclass of `DomainValidationError`) at line 70.
- `app/design_sync/tests/test_service_training_cases.py` — does **not** exist. Plan creates it.
- `app/design_sync/tests/test_routes_training_cases.py` — does **not** exist.

## Test Landscape

Existing `app/design_sync/tests/` (for reuse + extension):

| File | LOC | Role in this plan |
|------|-----|-------------------|
| `conftest.py` | 49 | `make_design_node()` + `make_file_structure()` protocol factories |
| `test_cta_fidelity.py` | 374 | **Bug 1 rewrite target** — 5 mechanical line edits. Untracked file (must `git add`). |
| `test_component_matcher.py` | 1667 | **Bug 1 add-location** — `_fills_social` currently untested. Has `_make_section()` helper at 24-55, `_button()` factory without `icon_url` param. |
| `test_component_renderer.py` | 473 | **Bug 2 add-location** — existing `_apply_token_overrides` tests at 268-308; `ComponentRenderer` fixture pattern: `r = ComponentRenderer(container_width=600); r.load(); return r`. |
| `test_service.py` | 1500 | `@pytest.mark.asyncio` convention established at 186-209. Bug 3 tests go in **new** `test_service_training_cases.py`. |
| `test_snapshot_regression.py` | — | Cases 5, 6, 10 auto-loaded from `data/debug/manifest.yaml`. `_MANIFEST` module-level path — do not monkeypatch. |

**Test conventions to follow** (all verified from existing tests):
- `ButtonElement(...)` is always constructed with named arguments. Rename is safe — no positional-args blast radius.
- `TokenOverride(css_property, target_class, value)` — positional (3 args).
- Each test file defines its own local `_make_section()` / `_button()` helpers; do not add to conftest.py.
- `monkeypatch.setattr("app.design_sync.service._DEBUG_DIR", ...)` pattern valid for Bug 3 (module-level paths override cleanly).
- No `type: ignore` comments reference `icon_url` or `_cta` anywhere in `app/design_sync/` — rename + scoping changes shouldn't require any ignore-list updates.

## Type Check Baseline

Pre-fix baseline — we own the delta, not the pre-existing errors. Do not regress per-file counts; do not be responsible for fixing the totals.

| File | Pyright errors | Pyright warnings |
|------|---------------:|-----------------:|
| `figma/layout_analyzer.py` | 5 | 1 |
| `component_matcher.py` | 1 | 0 |
| `component_renderer.py` | 2 | 0 |
| `service.py` | 66 | 3 |
| `routes.py` | 0 | 4 |
| `exceptions.py` | 0 | 0 |
| `tests/` (whole subtree) | 74 | 241 |
| **`app/design_sync/` total** | **276** | **343** |

Mypy total across `app/design_sync/`: **96 errors in 12 files**.

**Test suite baseline** (pre-fix): **1846 passed, 9 failed, 37 skipped** (1892 run; 5 additional files skipped due to missing `cssselect` / `hypothesis` / `skimage` — unrelated to this plan).

Pre-existing failures — not our responsibility, with caveats marked ⚠ below:
1. `test_builder_annotations.py::TestTextAnnotations::test_heading_gets_slot_name`
2. `test_builder_annotations.py::TestTextAnnotations::test_body_text_gets_slot_name`
3. `test_correction_tracker.py::TestApiEndpoints::test_approve_invalid_hash_format`
4. `test_snapshot_regression.py::test_snapshot_matches[6]` ⚠ see note
5. `test_snapshot_regression.py::test_snapshot_matches[10]` ⚠ expected to clear after Bug 2 + snapshot regen
6. `test_snapshot_regression.py::test_background_continuity[6]` ⚠ see note
7. `test_snapshot_regression.py::test_background_continuity[10]` ⚠ expected to clear
8. `test_spacing_pipeline.py::test_no_padding_no_wrapper`
9. `test_tree_bridge.py::TestRoundtripTreeToHtml::test_tree_compiles_to_valid_html`

Case 10 failures (5, 7) should clear after Bug 2 — the working-tree corruption is exactly the CTA-unscoped-regex symptom. Case 6 failures (4, 6) touch `class="textblock-bg"` which is **not** a CTA host; Bug 2's scoping change won't rewrite that element. Investigate separately before assuming case 6 is covered. Failures 1-3, 8, 9 are independent.

## Preflight Warnings

1. **Working tree has local edits** to 5 target source files (`component_renderer.py`, `exceptions.py`, `figma/layout_analyzer.py`, `routes.py`, `service.py`) and the 3 debug fixtures (`data/debug/{5,6,10}/expected.html`). Before editing each file, `git diff <file>` to see whether partial fixes from a prior attempt exist; isolate ultrareview work into its own commits per CLAUDE.md "Parallel Work Awareness".

   **Snapshot fixture asymmetry** (verified during planning). The 3 fixtures are **not** in the same state — case 10 is reversed from cases 5/6:

   | Case | HEAD (git blob) | Working tree (`M`) | Ground truth lives in | Backup source |
   |------|-----------------|--------------------|-----------------------|---------------|
   | 5 | `background-color:#FFFFFF` (buggy) | `background-color:#222222` (correct hand-edit) | working tree | `cp` working tree |
   | 6 | `background-color:#F7F0E3` (buggy) | `background-color:#006241` (correct hand-edit) | working tree | `cp` working tree |
   | 10 | `#FE5117` outer + `#0066cc` inner CTA (correct) | both flattened to `#FFFFFF` (buggy) | HEAD | `git show HEAD:data/debug/10/expected.html` |

   This matters for Bug 2's snapshot regeneration — use the per-case backup commands in the Bug 2 section below, **not** a uniform `cp` loop. After `make snapshot-capture`, diff captured output against the backup to confirm the post-fix converter produces the correct ground truth.

2. **`test_cta_fidelity.py` is untracked** (`?? app/design_sync/tests/test_cta_fidelity.py`). Must be `git add`-ed with specific path when committing Bug 1 — never use `git add -A`.

3. **Bug 2 regex anchors on attribute order** (`class="cta-..."` before `style="..."`, `data-slot="cta_url"` before `style="..."`). Verified across all 150 current templates. Silent-fail mode if a future template reorders — the defensive `test_cta_override_skips_style_before_data_slot_regression` locks this down via CI.

4. **Bug 3 doesn't add a lock.** Concurrent `create_training_case` requests with the same id could still both pass the manifest check. Acceptable because the endpoint is admin-only + low QPS; flagged for posterity.

5. **`_update_vml_arcsize` stays globally scoped in Bug 2** — only one production template (`cta-button.html`) emits `<v:roundrect>` today, at most once. Scoping adds code for no gain.

## Files to Create / Modify

| File | Bug | Change |
|------|-----|--------|
| `app/design_sync/figma/layout_analyzer.py` | 1 | Field rename (line 104) + kwarg rename (line 1085) |
| `app/design_sync/component_matcher.py` | 1 | Rewire `_fills_social` lookup (6 LOC at 1217-1222) |
| `app/design_sync/tests/test_cta_fidelity.py` | 1 | 5 mechanical `icon_url` → `icon_node_id` replacements; `git add` |
| `app/design_sync/tests/test_component_matcher.py` | 1 | Append 2 new `_fills_social` tests |
| `app/design_sync/component_renderer.py` | 2 | New scoped helpers (`_replace_cta_css_prop`, `_replace_cta_background_color`, `_replace_cta_bgcolor_attr`, `_replace_cta_fillcolor`, `_replace_cta_strokecolor` + module-level regex templates) + dispatch rewrite at 557-571 |
| `app/design_sync/tests/test_component_renderer.py` | 2 | 5 new scoping + regression tests (incl. defensive ordering) |
| `app/design_sync/service.py` | 3 | Hoist manifest check above mkdir (lines 1862-1868 → after 1832) |
| `app/design_sync/tests/test_service_training_cases.py` | 3 | **NEW FILE** — 2 async tests |
| `data/debug/{5,6,10}/expected.html` | 2 | Regenerate via `make snapshot-capture CASE=…` |

## Execution order

Do in this order — each bug is independent, but #2 is the largest diff and has the highest regression surface, so ship #1 and #3 first.

1. **Bug 1 (icon_url rename)** — 1 field rename + consumer + 5 test-line updates. ~15 LOC diff. Low risk.
2. **Bug 3 (training case ordering)** — 1 code-block reorder + 1 test. ~20 LOC diff. Low risk.
3. **Bug 2 (CTA scoping)** — 1 new helper + 4 call-site swaps + tests. ~60 LOC diff. Medium risk — touches every converter CTA output.

Verify after each with `make test` scoped to `app/design_sync/tests/` and then regenerate affected snapshot baselines (cases 5, 6, 10 for bug 2).

---

## Bug 1 — `ButtonElement.icon_url` stores a Figma node ID

**File refs:**
- Field def: `app/design_sync/figma/layout_analyzer.py:104`
- Producer (writes node id into `icon_url`): `app/design_sync/figma/layout_analyzer.py:1060-1086`
- Consumer: `app/design_sync/component_matcher.py:1218-1221`
- Tests referencing the field: `app/design_sync/tests/test_cta_fidelity.py:105, 113, 117, 198, 207`

### What's wrong today

`_walk_for_buttons` detects a small `VECTOR`/`FRAME`/`IMAGE` child named `icon` inside a button frame, captures the child's node id into local `icon_node_id`, then constructs `ButtonElement(..., icon_url=icon_node_id)`. The field name says URL, the value is a node id. No resolution step exists.

Consumer `_fills_social` then does:
```python
icon_url = btn.icon_url               # e.g. "2833:1172" — truthy
if not icon_url and image_urls:       # skipped because truthy
    icon_url = image_urls.get(btn.node_id) or ""
if not icon_url:                      # skipped
    continue
icon_src = html.escape(icon_url)      # "2833:1172" unchanged (':' isn't escaped)
cells.append(f'<img src="{icon_src}" ...>')
```

Output: `<img src="2833:1172" ...>` — broken relative URL. Affects every social-icon section whose Figma buttons have an `icon` child, i.e. the exact case the detection was added for.

Note the fallback `image_urls.get(btn.node_id)` also has a secondary latent bug: it looks up the button frame's id rather than the icon child's id. That fallback never fires today because of the short-circuit, but the scoping is wrong regardless.

### Fix

Rename the field and route the lookup through `image_urls` at the consumer. Matches the existing `ImagePlaceholder.export_node_id` convention.

**Change 1 — `app/design_sync/figma/layout_analyzer.py:104`:**
```python
# BEFORE
icon_url: str | None = None
# AFTER
icon_node_id: str | None = None
```

**Change 2 — `app/design_sync/figma/layout_analyzer.py:1085`:**
```python
# BEFORE
icon_url=icon_node_id,
# AFTER
icon_node_id=icon_node_id,
```

**Change 3 — `app/design_sync/component_matcher.py:1217-1222`:**
```python
for idx, btn in enumerate(section.buttons):
    icon_src: str = ""
    if btn.icon_node_id and image_urls:
        icon_src = image_urls.get(btn.icon_node_id) or ""
    if not icon_src and image_urls:
        icon_src = image_urls.get(btn.node_id) or ""
    if not icon_src:
        continue
```

Key points:
- Primary lookup: icon child's node id (the fix).
- Preserve the button-frame fallback (rendering a social icon when the button itself is image-based and has no icon child — this is the pre-41.x behaviour).
- Rename the local from `icon_url` → `icon_src`: after the lookup it holds a resolved URL, and keeping the misleading `icon_url` name is the exact pattern that caused the original bug. Update the subsequent `html.escape(icon_url)` and f-string `src="{icon_src}"` accordingly.
- No stray uses of `btn.icon_url` survive (grep confirms `icon_url` only appears in `layout_analyzer.py:104,1085` + `component_matcher.py:1218` + `test_cta_fidelity.py:105,113,117,198,207`).

**Change 4 — `app/design_sync/tests/test_cta_fidelity.py`:** 5 lines, mechanical s/icon_url/icon_node_id/. Specifically:
- line 105: `assert btn.icon_url is None` → `icon_node_id`
- line 113: `icon_url="icon_node_1"` → `icon_node_id="icon_node_1"`
- line 117: `assert btn.icon_url == "icon_node_1"` → `icon_node_id`
- line 198: `assert results[0].icon_url == "icon_1"` → `icon_node_id`
- line 207: `assert results[0].icon_url is None` → `icon_node_id`

### New tests

Add one integration-style unit test in `app/design_sync/tests/test_component_matcher.py` (or wherever `_fills_social` is currently tested):

```python
def test_fills_social_resolves_icon_node_id_via_image_urls() -> None:
    section = _make_section_with_button(
        button=ButtonElement(
            node_id="btn_1",
            text="Twitter",
            url="https://twitter.com/acme",
            icon_node_id="icon_42",
        ),
    )
    image_urls = {"icon_42": "https://cdn.example.com/icons/twitter.png"}
    fills = _fills_social(section, 600, image_urls=image_urls)
    assert len(fills) == 1
    row = fills[0].value
    assert "https://cdn.example.com/icons/twitter.png" in row
    assert "icon_42" not in row  # raw node id must NOT leak into src=
```

And a second test asserting the old bug no longer reproduces:

```python
def test_fills_social_does_not_emit_raw_node_id_in_src() -> None:
    section = _make_section_with_button(
        button=ButtonElement(
            node_id="btn_1",
            text="Twitter",
            url="https://twitter.com/acme",
            icon_node_id="2833:1172",
        ),
    )
    # No image_urls → button should be skipped, not rendered with a broken src.
    fills = _fills_social(section, 600, image_urls=None)
    assert fills == [] or '"2833:1172"' not in fills[0].value
```

### Verification

- `pytest app/design_sync/tests/test_cta_fidelity.py app/design_sync/tests/test_component_matcher.py -x`
- `rg -n "\.icon_url\b" app/design_sync/` returns zero hits after the change.

---

## Bug 2 — `_cta` token overrides use unscoped regexes

**File refs:**
- Dispatch branch: `app/design_sync/component_renderer.py:557-571`
- Existing scoped helper to emulate: `app/design_sync/component_renderer.py:639-653` (`_CTA_LINK_COLOR_RE` + `_replace_cta_text_color`)
- Unscoped helper being misused: `app/design_sync/component_renderer.py:634-637` (`_replace_css_prop_all`)
- Template shapes that expose the bug:
  - Standalone button (CTA lives on the outer table): `email-templates/components/button-filled.html:3`, `button-ghost.html:3`, `cta-button.html:12` — all tables carry `class="cta-btn"` or `class="cta-ghost"`.
  - Inline CTA inside a card (CTA lives on an inner `<a data-slot="cta_url">`): `event-card.html:23`, `product-card.html:22`, plus all pricing-table / testimonial-card variants.
  - Both cases in the same component: event-card's outer `<table class="event-card" style="... border-radius: 8px;">` vs inner `<a data-slot="cta_url" style="... border-radius: 4px;">`.

### What's wrong today

```python
elif target == "_cta":
    if prop == "background-color":
        result = re.sub(r'bgcolor="[^"]*"', f'bgcolor="{val}"', result)                  # unscoped
        result = self._replace_css_prop_all(result, "background-color", val)             # unscoped
        result = re.sub(r'fillcolor="[^"]*"', f'fillcolor="{val}"', result)              # unscoped
    elif prop == "color":
        result = self._replace_cta_text_color(result, val)                               # SCOPED ✓
    elif prop == "border-radius":
        result = self._replace_css_prop_all(result, "border-radius", val)                # unscoped
        result = self._update_vml_arcsize(result, val)                                   # unscoped
    elif prop == "border-color":
        result = re.sub(r'strokecolor="[^"]*"', f'strokecolor="{val}"', result)          # unscoped
        result = self._replace_css_prop_all(result, "border-color", val)                 # unscoped
    elif prop == "border-width":
        result = self._replace_css_prop_all(result, "border-width", val)                 # unscoped
```

Only the `color` sub-branch already does the right thing (it restricts to `<a ... data-slot="cta_url" ...>`). Every other sub-branch rewrites every matching declaration in the rendered component, which clobbers adjacent non-CTA styles in composite templates.

Concrete failure in `data/debug/10/expected.html` (already checked-in as a modified fixture): outer `#FE5117` card background and inner `#0066cc` button background both flattened to `#FFFFFF`. Same class of bug rewrites `border-radius: 8px` on `event-card` → `4px` whenever the Figma button declares its own radius.

### Fix

Introduce a `_cta`-scoped property replacement helper that recognises both CTA hosts:

1. An element carrying `class="cta-btn"` or `class="cta-ghost"` (used by standalone button templates — all three button components set this; `cta-button.html:12` confirms).
2. `<a ... data-slot="cta_url" ...>` (used by inline CTAs inside cards).

**Add module-level patterns and helper, `app/design_sync/component_renderer.py` near line 638:**

```python
# CTA-scoped CSS property replacement.
# Matches a CSS declaration inside the style attribute of either:
#   (a) a <table>/<td>/<div>/<a> whose class contains "cta-btn" or "cta-ghost"
#   (b) an <a data-slot="cta_url"> (inline CTA inside cards like event-card)
# Anchor groups: \g<1> preserves everything from the tag open through the
# property name; \g<2> preserves the trailing ';' (or empty). Caller fills
# in prop name + literal replacement.
_CTA_CLASS_STYLE_RE_TEMPLATE = (
    r'(<[^>]*\bclass="(?:[^"]*\s)?cta-(?:btn|ghost)(?:\s[^"]*)?"[^>]*style="[^"]*?)'
    r'(?<!background-){prop}:\s*[^;"]+(;?)'
)
_CTA_LINK_STYLE_RE_TEMPLATE = (
    r'(<a\b[^>]*data-slot="cta_url"[^>]*style="[^"]*?)'
    r'(?<!background-){prop}:\s*[^;"]+(;?)'
)

def _replace_cta_css_prop(self, html_str: str, prop: str, value: str) -> str:
    """Replace a CSS property on CTA elements only (cta-btn/cta-ghost class or data-slot='cta_url')."""
    safe_prop = re.escape(prop)
    safe_value = html.escape(value, quote=True)
    repl = rf"\g<1>{prop}:{safe_value}\g<2>"
    class_pattern = _CTA_CLASS_STYLE_RE_TEMPLATE.format(prop=safe_prop)
    slot_pattern = _CTA_LINK_STYLE_RE_TEMPLATE.format(prop=safe_prop)
    result = re.sub(class_pattern, repl, html_str)
    return re.sub(slot_pattern, repl, result)
```

Notes:
- The `(?<!background-)` lookbehind is dead weight here — none of `border-radius` / `border-color` / `border-width` / `background-color` collide with other props via shared suffix. Drop it from `_CTA_CLASS_STYLE_RE_TEMPLATE` and `_CTA_LINK_STYLE_RE_TEMPLATE`; the background-color helper below omits it.
- **Attribute ordering assumption:** the regex requires `class="...cta-btn..."` before `style="..."` in the same opening tag (likewise `data-slot="cta_url"` before `style="..."` on inline anchors). Verified across all 150 templates via `rg -l 'class="[^"]*cta-(btn|ghost)' email-templates/components/ | xargs rg -n 'style="[^"]*".*class="[^"]*cta-(btn|ghost)'` → 0 hits. A future reorder would silently fail to apply the token; the defensive ordering test below locks it down.

**Replace the `_cta` dispatch in `_apply_token_overrides`, `app/design_sync/component_renderer.py:557-571`:**

```python
elif target == "_cta":
    if prop == "background-color":
        result = self._replace_cta_background_color(result, val)
        result = self._replace_cta_bgcolor_attr(result, val)
        result = self._replace_cta_fillcolor(result, val)
    elif prop == "color":
        result = self._replace_cta_text_color(result, val)
    elif prop == "border-radius":
        result = self._replace_cta_css_prop(result, "border-radius", val)
        result = self._update_vml_arcsize(result, val)  # stays global — only cta-button.html emits VML
    elif prop == "border-color":
        result = self._replace_cta_css_prop(result, "border-color", val)
        result = self._replace_cta_strokecolor(result, val)
    elif prop == "border-width":
        result = self._replace_cta_css_prop(result, "border-width", val)
```

**Add sibling helpers for the attribute-based and background-color cases:**

```python
_CTA_BGCOLOR_ATTR_RE = re.compile(
    r'(<[^>]*\bclass="(?:[^"]*\s)?cta-(?:btn|ghost)(?:\s[^"]*)?"[^>]*)\bbgcolor="[^"]*"'
)
_CTA_FILLCOLOR_RE = re.compile(r'(<v:roundrect\b[^>]*)\bfillcolor="[^"]*"')
_CTA_STROKECOLOR_RE = re.compile(r'(<v:roundrect\b[^>]*)\bstrokecolor="[^"]*"')

def _replace_cta_bgcolor_attr(self, html_str: str, color: str) -> str:
    safe = html.escape(color, quote=True)
    return self._CTA_BGCOLOR_ATTR_RE.sub(rf'\g<1>bgcolor="{safe}"', html_str)

def _replace_cta_fillcolor(self, html_str: str, color: str) -> str:
    safe = html.escape(color, quote=True)
    return self._CTA_FILLCOLOR_RE.sub(rf'\g<1>fillcolor="{safe}"', html_str)

def _replace_cta_strokecolor(self, html_str: str, color: str) -> str:
    safe = html.escape(color, quote=True)
    return self._CTA_STROKECOLOR_RE.sub(rf'\g<1>strokecolor="{safe}"', html_str)
```

**Background-color variant of the scoped helper (drops the `background-` lookbehind):**

```python
_CTA_CLASS_BG_RE_TEMPLATE = (
    r'(<[^>]*\bclass="(?:[^"]*\s)?cta-(?:btn|ghost)(?:\s[^"]*)?"[^>]*style="[^"]*?)'
    r'background-color:\s*[^;"]+(;?)'
)
_CTA_LINK_BG_RE_TEMPLATE = (
    r'(<a\b[^>]*data-slot="cta_url"[^>]*style="[^"]*?)'
    r'background-color:\s*[^;"]+(;?)'
)

def _replace_cta_background_color(self, html_str: str, color: str) -> str:
    safe = html.escape(color, quote=True)
    repl = rf"\g<1>background-color:{safe}\g<2>"
    result = re.sub(_CTA_CLASS_BG_RE_TEMPLATE, repl, html_str)
    return re.sub(_CTA_LINK_BG_RE_TEMPLATE, repl, result)
```

### Why `_update_vml_arcsize` stays global

`<v:roundrect>` only appears in button-filled/button-ghost/cta-button templates — none of the card/zigzag/pricing templates emit VML roundrects. A single rendered component yields at most one VML roundrect today. Scoping adds code with no behavioural gain. Leave as-is; note this in a one-liner comment at the call site.

### Tests

Add to `app/design_sync/tests/test_component_renderer.py` (or next to existing override tests):

```python
def test_cta_border_radius_override_does_not_clobber_outer_card_radius() -> None:
    # Simulated event-card output: outer table + inner anchor, both with their
    # own border-radius. Applying a _cta override should only touch the inner.
    html_in = (
        '<table class="event-card" style="border-radius: 8px;">'
        '<tr><td><a data-slot="cta_url" style="padding: 12px; border-radius: 4px;">Go</a></td></tr>'
        '</table>'
    )
    renderer = ComponentRenderer(...)
    overrides = [TokenOverride("border-radius", "_cta", "6px")]
    out = renderer._apply_token_overrides(html_in, overrides)
    assert 'class="event-card" style="border-radius: 8px;"' in out
    assert "border-radius: 6px" in out
    assert out.count("border-radius: 8px") == 1  # outer preserved

def test_cta_background_override_does_not_clobber_outer_card_bg() -> None:
    html_in = (
        '<table class="event-card" style="background-color: #FE5117;">'
        '<tr><td><a data-slot="cta_url" style="background-color: #0066cc;">Go</a></td></tr>'
        '</table>'
    )
    renderer = ComponentRenderer(...)
    out = renderer._apply_token_overrides(
        html_in, [TokenOverride("background-color", "_cta", "#00AA88")]
    )
    assert "#FE5117" in out           # outer preserved
    assert "#00AA88" in out           # CTA updated
    assert "#0066cc" not in out       # CTA's old value replaced

def test_cta_border_color_override_scoped_to_cta_class() -> None:
    html_in = (
        '<table class="event-card" style="border-color: #cccccc;">'
        '<tr><td><table class="cta-btn" style="border-color: #1a1a1a;">'
        '<tr><td><a data-slot="cta_url" style="border-color: #1a1a1a;">x</a></td></tr>'
        '</table></td></tr></table>'
    )
    renderer = ComponentRenderer(...)
    out = renderer._apply_token_overrides(
        html_in, [TokenOverride("border-color", "_cta", "#FF0000")]
    )
    assert "border-color: #cccccc" in out
    assert out.count("#FF0000") >= 1
```

Also add one regression test pinned to the observed `data/debug/10` corruption:

```python
def test_cta_background_override_preserves_outer_hero_hex() -> None:
    # Repro of data/debug/10 regression: outer hero had #FE5117, inner CTA
    # had #0066cc. Before the fix, both flattened to CTA override value.
    ...
```

And one defensive ordering test — this is the fragile assumption flagged during review:

```python
def test_cta_override_handles_data_slot_before_style_only() -> None:
    # The scoped regex assumes data-slot appears before style within the
    # same <a> tag. If a future template reorders, the override silently
    # fails (no error — wrong color shipped). Lock the assumption down.
    html_in = '<a data-slot="cta_url" href="#" style="border-radius: 4px;">x</a>'
    renderer = ComponentRenderer(...)
    out = renderer._apply_token_overrides(
        html_in, [TokenOverride("border-radius", "_cta", "6px")]
    )
    assert "border-radius: 6px" in out

def test_cta_override_skips_style_before_data_slot_regression() -> None:
    # Documents the current limitation: if a template author ever writes
    # style before data-slot on the <a>, the override will NOT apply. The
    # test ensures we notice (via CI failure) rather than silently ship
    # wrong colors. Flip the assertion and widen the regex if we ever see
    # this shape in a real template.
    html_in = '<a style="border-radius: 4px;" data-slot="cta_url" href="#">x</a>'
    renderer = ComponentRenderer(...)
    out = renderer._apply_token_overrides(
        html_in, [TokenOverride("border-radius", "_cta", "6px")]
    )
    # Known limitation — outer [^>]* in regex requires data-slot before style.
    assert "border-radius: 4px" in out
```

### Snapshot regeneration

**Pre-capture backup** — ground truth lives in different places per case (see Preflight #1 asymmetry table):

```bash
# Cases 5 & 6: working tree IS the correct hand-edit — copy it.
cp data/debug/5/expected.html /tmp/case5-expected.html
cp data/debug/6/expected.html /tmp/case6-expected.html
# Case 10: working tree is the buggy flattened output; HEAD has the correct Figma values.
git show HEAD:data/debug/10/expected.html > /tmp/case10-expected.html
```

After the fix lands:
```bash
make snapshot-capture CASE=5
make snapshot-capture CASE=6
make snapshot-capture CASE=10
```

Compare captured output against the backed-up ground truth:
```bash
diff /tmp/case5-expected.html data/debug/5/expected.html
diff /tmp/case6-expected.html data/debug/6/expected.html
diff /tmp/case10-expected.html data/debug/10/expected.html
```

Expected result: **the post-fix converter output matches the backed-up ground truth** — outer card's `background-color` / `border-radius` / `border-color` remain at the Figma-designed values instead of getting stomped. If case 10's diff still shows `#FFFFFF` where HEAD had `#FE5117` / `#0066cc`, the fix is incomplete; roll back and investigate. Case 6 is not guaranteed to converge here — its diff is on `class="textblock-bg"` (not a CTA host). If the diff shows a different-but-plausibly-correct output (whitespace, attribute ordering), accept the captured version as the new baseline. Then `make snapshot-test` to lock in.

### Risk

Medium. The fix narrows a regex that previously swallowed every match, so the worst-case regression is "a CTA property didn't get applied somewhere it used to". The scoped regex covers both CTA host shapes found in the 150-component library; run the full `pytest app/design_sync/tests/` plus `make golden-conformance` to catch anything outside.

---

## Bug 3 — `create_training_case` leaves partial state on manifest drift

**File refs:**
- `app/design_sync/service.py:1808-1895` (function body)
- `app/design_sync/service.py:1862-1868` (manifest duplicate check — currently AFTER file writes)
- `app/design_sync/routes.py:992-1031` (handler; maps `TrainingCaseExistsError` → 409)

### What's wrong today

Order of operations:

1. `_validate_case_id(case_id)` — syntactic only.
2. `if case_dir.exists(): raise TrainingCaseExistsError` — catches the common case (dir still there).
3. `mkdir(parents=True, exist_ok=True)` — creates `data/debug/{case_id}/`.
4. Write `expected.html`.
5. Optionally write `design.png`.
6. Read manifest, check for `id: "{case_id}"` substring.
7. Raise `TrainingCaseExistsError` if duplicate.

Failure mode: manifest has `id: "{case_id}"` but the directory was deleted out-of-band (cleanup script, hand-edit, partial previous run that errored mid-write). Then:

- Step 2 passes (`case_dir.exists()` → False).
- Step 3 creates the dir.
- Step 4 writes `expected.html`.
- Step 6 finds the duplicate.
- Step 7 raises 409.

Directory now exists, `expected.html` now exists, manifest is unchanged. On retry, step 2 fails immediately — 409 forever. Requires out-of-band `rm -rf` to recover, which the HTTP caller does not have.

### Fix (option A, preferred — mechanical hoist)

Move the manifest duplicate check above `mkdir`. Keep the `case_dir.exists()` guard to preserve the normal-case 409.

**`app/design_sync/service.py:1824-1874` — reordered:**

```python
_validate_case_id(case_id)

case_dir = _DEBUG_DIR / case_id
if case_dir.exists():
    raise TrainingCaseExistsError(f"Training case '{case_id}' already exists")

if not html_content.strip():
    raise TrainingCaseError("HTML content is empty")

# Check manifest BEFORE creating the directory. If the manifest still
# carries a stale entry for a case whose dir was deleted, we must not
# leave partial files on disk — subsequent retries would then trip the
# case_dir.exists() guard above and be permanently rejected.
if _MANIFEST_PATH.exists():
    existing_text = _MANIFEST_PATH.read_text()
    if f'id: "{case_id}"' in existing_text:
        raise TrainingCaseExistsError(f"Case '{case_id}' already in manifest")

log = get_logger(__name__)
files_written: list[str] = []

case_dir.mkdir(parents=True, exist_ok=True)

# Write expected.html
(case_dir / "expected.html").write_text(html_content, encoding="utf-8")
files_written.append("expected.html")

# ... (screenshot + manifest append + figma_meta as before) ...
```

Concretely, merge the existing lines 1862-1868 up to just after line 1832 (the empty-HTML guard). The manifest append block (lines 1870-1873) stays where it is — it only runs now that we know the id is not a dup.

### Belt-and-suspenders (optional, **not in this patch**)

A stricter fix would wrap the mkdir + writes in try/except with `shutil.rmtree(case_dir, ignore_errors=True)` in the except branch to cover mid-write failures (disk full, permission errors after mkdir). Explicitly deferred — it broadens fix scope, muddies the traceback's filesystem context, and we have no evidence of mid-write failures in practice. Land the hoist first; add cleanup as a separate patch if a real incident surfaces.

### New tests

Add to `app/design_sync/tests/test_service_training_cases.py` (create if it doesn't exist — none found today):

```python
@pytest.mark.asyncio
async def test_create_training_case_rejects_manifest_duplicate_without_writing_files(
    tmp_path: Path, monkeypatch: MonkeyPatch,
) -> None:
    # Point the module at a temp data/debug, seed a manifest with a stale id.
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    manifest_path = debug_dir / "manifest.yaml"
    manifest_path.write_text('cases:\n  - id: "ghost"\n    name: "Stale"\n')

    monkeypatch.setattr("app.design_sync.service._DEBUG_DIR", debug_dir)
    monkeypatch.setattr("app.design_sync.service._MANIFEST_PATH", manifest_path)

    # The directory does NOT exist (simulates out-of-band deletion).
    with pytest.raises(TrainingCaseExistsError):
        await create_training_case(
            case_id="ghost",
            case_name="Ghost",
            html_content="<html></html>",
        )

    # Critical assertion: no partial state left behind.
    assert not (debug_dir / "ghost").exists()
    # Manifest untouched.
    assert manifest_path.read_text().count('id: "ghost"') == 1


@pytest.mark.asyncio
async def test_create_training_case_allows_retry_after_manifest_fix(
    tmp_path: Path, monkeypatch: MonkeyPatch,
) -> None:
    debug_dir = tmp_path / "debug"
    debug_dir.mkdir()
    manifest_path = debug_dir / "manifest.yaml"
    manifest_path.write_text('cases:\n  - id: "ghost"\n    name: "Stale"\n')

    monkeypatch.setattr("app.design_sync.service._DEBUG_DIR", debug_dir)
    monkeypatch.setattr("app.design_sync.service._MANIFEST_PATH", manifest_path)

    with pytest.raises(TrainingCaseExistsError):
        await create_training_case(case_id="ghost", case_name="Ghost", html_content="<x/>")

    # Remove the stale manifest entry (simulates operator cleanup).
    manifest_path.write_text("cases: []\n")

    # Retry must succeed — pre-fix this raised because the dir already existed.
    result = await create_training_case(case_id="ghost", case_name="Ghost", html_content="<x/>")
    assert result["case_id"] == "ghost"
    assert (debug_dir / "ghost" / "expected.html").exists()
```

### Verification

- `pytest app/design_sync/tests/test_service_training_cases.py -x`
- `rg -n "case_dir.mkdir|_MANIFEST_PATH.exists" app/design_sync/service.py` — confirm mkdir now follows the manifest read block.

### Risk

Low. Pure reorder; no new dependencies; the existing `case_dir.exists()` guard remains for the normal duplicate case.

---

## Cross-cutting verification

After all three fixes land:

1. `pytest app/design_sync/tests/ -x` — unit tests. Expect delta: **+10 new tests** (Bug 1 ×2 `_fills_social`, Bug 2 ×6 = 3 scoping + 1 `data/debug/10` regression + 2 defensive ordering, Bug 3 ×2 async training-case). Pre-existing case-10 failures (5, 7 in the baseline list) should clear after step 5; case-6 failures (4, 6) may not — `textblock-bg` is not a CTA host.
2. `make golden-conformance` — the 14-template conformance gate.
3. `make lint` + `make types` — ruff + mypy + pyright strict. Per-file baseline: layout_analyzer=5 errors, component_matcher=1, component_renderer=2, service.py=66 (pre-existing), routes=0, exceptions=0. Do not regress.
4. `make converter-data-regression` — the 4-case manifest-driven regression runner added in 49.9. Expect fidelity on cases 5/6/10 to *improve* (border-radius and background-color no longer corrupted) and MAAP/Starbucks/Mammut to stay stable.
5. `make snapshot-capture CASE=5`, `6`, `10` to regenerate baselines; diff review; then `make snapshot-test` to lock.
6. Manual: POST to `/api/v1/design-sync/training-cases` with a `case_id` whose manifest entry exists but directory doesn't — expect 409, no files written, subsequent retry after manifest cleanup succeeds.

## Security Checklist

Per `_shared/backend-security-scoped.md`. Scoped to the touched surface area:

- **Input validation:** Bug 1 + Bug 2 touch only internal data structures (`ButtonElement`, token overrides from Figma). Bug 3's `html_content` is already admin-only and non-rendered by the API (stored as a training fixture, not served to end users). No new input surface.
- **Authorization:** No new endpoints. Existing `/api/v1/design-sync/training-cases` remains admin-role-only via the existing `routes.py` dependency.
- **Error-message leakage:** `TrainingCaseExistsError` message format unchanged (still "Training case '{case_id}' already exists" — no internal paths leaked).
- **XSS / injection:** `_replace_cta_css_prop` uses `html.escape(value, quote=True)` before substitution. New regex helpers anchor on attribute boundaries — no value-in-value substitution risk. Icon URL rename removes a broken-src-leak route (was "2833:1172" into `src=`).
- **Rate limiting:** Untouched — existing limiter stays on `/training-cases` route.

## Not in scope

- Scoping `_update_vml_arcsize` / attribute-based `fillcolor`/`strokecolor` more tightly than the new helpers do. Today only one VML roundrect per component exists; revisit when we ship `cta-pair` with real VML.
- The `image_urls.get(btn.node_id)` secondary fallback in `_fills_social`. Kept as-is for backwards compat; if we later find it never matches real data, remove it in a follow-up.
- The mid-write cleanup try/except in `create_training_case`. Ship the hoist first; add rollback only if we see real incidents.
- Acquiring a lock for concurrent `create_training_case` calls — admin-only endpoint with low QPS.
