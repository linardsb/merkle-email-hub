# Plan: 48.8 Component Tree Deterministic Compiler

## Context

Add `TreeCompiler` that walks an `EmailTree` and produces complete email HTML. The compilation is 100% deterministic — no LLM. Identical input → identical output, enabling caching, diffing, and regression testing.

## Research Summary

| File | Role |
|------|------|
| `app/components/tree_schema.py` | `EmailTree`, `TreeSection`, `TreeMetadata`, `SlotValue` (discriminated union: `TextSlot`/`ImageSlot`/`ButtonSlot`/`HtmlSlot`), `validate_tree_against_manifest()` |
| `app/components/data/seeds.py` | Email Shell inline HTML (document boilerplate with DOCTYPE, VML, MSO, dark mode, responsive), `COMPONENT_SEEDS` list |
| `app/components/data/file_loader.py` | `load_file_components()` → YAML manifest + HTML from `email-templates/components/{slug}.html`, `_extract_slots_from_html()` auto-detects `data-slot` attrs |
| `app/components/data/component_manifest.yaml` | 150 component entries with `slug`, `slot_definitions[]`, `default_tokens` |
| `app/components/sanitize.py` | `sanitize_component_html()` — strips XSS vectors, preserves MSO/dark mode |
| `app/components/section_adapter.py` | `SectionAdapter` — existing component→section bridge (lxml DOM, slot injection, dark mode extraction) |
| `app/core/exceptions.py` | `DomainValidationError(AppError)` — correct parent for compile errors |
| `email-templates/components/*.html` | ~100 HTML files, each uses `data-slot="slot_id"` markers on `<td>`, `<a>`, `<span>` elements |

**Key patterns from existing templates:**
- `data-slot="headline"` on `<td>` → text content goes inside
- `data-slot="cta_url"` on `<a>` → href attr + text inside `<span data-slot="cta_text">`
- `data-slot="image_url"` on `<img>` or background table → src attr
- MSO conditionals (`<!--[if mso]>`) must be preserved through compilation
- Email Shell has `data-slot="email_body"` div where sections are injected

**Email Shell structure** (`seeds.py:22-144`):
- DOCTYPE + html with VML/Office namespaces
- Head: charset, viewport, color-scheme, format-detection metas
- MSO OfficeDocumentSettings conditional
- `<style>`: color-scheme root, body reset, img/table resets, responsive `@media max-width:599px`, dark mode `@media prefers-color-scheme:dark`, Outlook dark mode `[data-ogsc]`/`[data-ogsb]` selectors
- Body: `<div role="article">` → preheader hidden div → MSO 600px table wrapper → `<div data-slot="email_body" style="max-width:600px">` content area

## Test Landscape

**Existing test files in `app/components/tests/`:** 10 files including `test_tree_schema.py`, `test_sanitize.py`, `test_section_adapter.py`, `test_file_loader.py`, `test_new_components.py`

**Fixtures (`conftest.py`):** `make_component(**overrides)`, `make_version(**overrides)`, `sample_component`, `sample_components`, `mock_db`

**Test conventions:** Class-based grouping (`TestEmailTreeValidation`), `_make_*()` local factories, each XSS vector tested in isolation, `@pytest.mark.integration` for real-data tests

**Real data:** 150+ component HTML files, 15 golden templates in `app/ai/templates/library/`, `COMPONENT_SEEDS` list

## Type Check Baseline

- **Pyright:** 7 errors (5 in `test_file_loader.py` — `reportUnknownArgumentType`), 24 warnings (`reportPrivateUsage` — expected in tests)
- **Mypy:** 0 errors across 28 source files

## Files to Create/Modify

### Create

| File | Purpose |
|------|---------|
| `app/components/tree_compiler.py` | `TreeCompiler` class + `CompiledEmail` dataclass + `CompilationError` |
| `app/components/tests/test_tree_compiler.py` | 14 tests across 4 test classes |

### Modify

| File | Change |
|------|--------|
| `app/core/exceptions.py` | Add `CompilationError(DomainValidationError)` |

## Implementation Steps

### Step 1: Add `CompilationError` to exception hierarchy

`app/core/exceptions.py` — add after `CyclicDependencyError`:

```python
class CompilationError(DomainValidationError):
    """Tree-to-HTML compilation failure."""
```

### Step 2: Create `app/components/tree_compiler.py`

**Imports:**
```python
from __future__ import annotations

import hashlib
import html as html_lib
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.components.data.file_loader import _extract_slots_from_html, load_file_components
from app.components.data.seeds import COMPONENT_SEEDS
from app.components.sanitize import sanitize_component_html
from app.components.tree_schema import (
    ButtonSlot, EmailTree, HtmlSlot, ImageSlot, SlotValue, TextSlot, TreeSection,
    validate_tree_against_manifest,
)
from app.core.exceptions import CompilationError
from app.core.logging import get_logger
```

**`CompiledEmail` dataclass:**
```python
@dataclass(frozen=True, slots=True)
class CompiledEmail:
    html: str
    sections_compiled: int
    custom_sections: int
    compilation_ms: int
```

**`TreeCompiler` class outline:**

| Method | Responsibility |
|--------|---------------|
| `__init__(self, template_dir: Path \| None = None)` | Load manifest from `COMPONENT_SEEDS`, build `_slug_to_html: dict[str, str]`, `_slug_to_slots: dict[str, list[str]]`, `_shell_html: str` from email-shell, init `_cache: dict[tuple, str]` |
| `compile(self, tree: EmailTree) -> CompiledEmail` | Validate tree via `validate_tree_against_manifest()`, compile each section, inject into shell, return `CompiledEmail` |
| `_compile_section(self, section: TreeSection) -> str` | Route to `_compile_custom()` or `_compile_component()` |
| `_compile_custom(self, section: TreeSection) -> str` | Return `sanitize_component_html(section.custom_html)` |
| `_compile_component(self, section: TreeSection) -> str` | Load template HTML, fill slots via lxml, apply style overrides, return HTML string |
| `_fill_slot(self, element: HtmlElement, slot_id: str, value: SlotValue) -> None` | Dispatch to `_fill_text`/`_fill_image`/`_fill_button`/`_fill_html` |
| `_fill_text(self, el: HtmlElement, slot: TextSlot) -> None` | Set `el.text = html_lib.escape(slot.text)` |
| `_fill_image(self, el: HtmlElement, slot: ImageSlot) -> None` | Set `src`, `alt`, `width`, `height` attrs on `<img>` or create `<img>` child |
| `_fill_button(self, el: HtmlElement, slot: ButtonSlot) -> None` | Validate URL scheme, set `href`, `style` (bg/text color), set inner text |
| `_fill_html(self, el: HtmlElement, slot: HtmlSlot) -> None` | `sanitize_component_html(slot.html)`, parse and append children |
| `_apply_style_overrides(self, root: HtmlElement, overrides: dict[str, str]) -> None` | Merge overrides into root element's `style` attribute |
| `_inject_design_tokens(self, shell_html: str, tokens: dict[str, dict[str, str]]) -> str` | Replace CSS custom property defaults in `<style>` block with token values |
| `_build_shell(self, subject: str, preheader: str, body_html: str, dark_palette: dict[str, str]) -> str` | Fill email-shell slots: `email_title`, `preheader`, `email_body`; inject dark palette overrides if present |
| `_cache_key(self, section: TreeSection) -> tuple` | `(slug, md5(slot_fills_json), md5(style_overrides_json))` |

**Slot filling approach:**
1. Parse component HTML with `lxml.html.fragment_fromstring()` (or `fragments_fromstring()` for multi-root)
2. Find `data-slot` elements with `el.cssselect(f'[data-slot="{slot_id}"]')`
3. For each matched element, dispatch to type-specific filler
4. Serialize back with `lxml.html.tostring(el, encoding='unicode')`

**URL scheme validation for ButtonSlot.href:**
```python
_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel"})

def _validate_url_scheme(href: str) -> bool:
    scheme = href.split(":", 1)[0].lower() if ":" in href else ""
    return scheme in _SAFE_URL_SCHEMES
```

**Style override application:**
- Parse existing `style` attr into dict, merge overrides (overrides win), serialize back
- Only validated CSS property names reach here (Pydantic regex on `TreeSection`)

**Caching strategy:**
- `_section_cache: dict[tuple[str, str, str], str]` keyed by `(slug, slot_hash, override_hash)`
- MD5 of JSON-serialized slot_fills and style_overrides for cache key
- File mtime check on component HTML file — if changed, invalidate all entries for that slug
- `_file_mtimes: dict[str, float]` tracks last-seen mtime per slug

**Shell assembly:**
- Load email-shell HTML from `COMPONENT_SEEDS[0]` (slug='email-shell')
- Replace `data-slot="email_title"` text with `subject`
- Replace `data-slot="preheader"` text with `preheader`
- Replace `data-slot="email_body"` inner HTML with concatenated section HTML
- If `design_tokens` contains `dark_palette` key, inject additional `@media (prefers-color-scheme: dark)` rules into existing `<style>` block

### Step 3: Write tests — `app/components/tests/test_tree_compiler.py`

**Local factory:**
```python
def _make_tree(**overrides: Any) -> EmailTree:
    defaults = {
        "metadata": {"subject": "Test Email", "preheader": "Preview"},
        "sections": [{"component_slug": "hero-block", "slot_fills": {
            "headline": {"type": "text", "text": "Hello World"},
        }}],
    }
    defaults.update(overrides)
    return EmailTree.model_validate(defaults)
```

**Test classes and cases (14 tests):**

| # | Class | Test | Asserts |
|---|-------|------|---------|
| 1 | `TestCompile` | `test_single_section_valid_html` | Compile 1-section tree → `<!DOCTYPE` + `<html` + section content present |
| 2 | `TestCompile` | `test_five_sections_all_rendered` | 5 sections → `sections_compiled == 5` + all content present in order |
| 3 | `TestCompile` | `test_custom_section_uses_provided_html` | `__custom__` section → `custom_html` in output, `custom_sections == 1` |
| 4 | `TestCompile` | `test_unknown_slug_raises_compilation_error` | Unknown slug → `CompilationError` |
| 5 | `TestSlotFilling` | `test_text_slot_fills_content` | `TextSlot("Hello")` → "Hello" in `<td data-slot>` |
| 6 | `TestSlotFilling` | `test_image_slot_generates_img` | `ImageSlot(src, alt, w, h)` → `<img src=... alt=... width=... height=...>` |
| 7 | `TestSlotFilling` | `test_button_slot_generates_link` | `ButtonSlot(text, href, colors)` → `<a href=...>` with inline bg/text color |
| 8 | `TestSlotFilling` | `test_button_slot_rejects_javascript_href` | `ButtonSlot(href="javascript:alert(1)")` → `CompilationError` |
| 9 | `TestSlotFilling` | `test_html_slot_sanitized` | `HtmlSlot("<script>alert(1)</script><b>ok</b>")` → no `<script>`, `<b>ok</b>` present |
| 10 | `TestStyleOverrides` | `test_style_override_applied_to_root` | `style_overrides={"background-color": "#FF0000"}` → `background-color: #FF0000` in root element style |
| 11 | `TestDocumentStructure` | `test_dark_mode_media_query_present` | Default compile → `prefers-color-scheme: dark` in output |
| 12 | `TestDocumentStructure` | `test_mso_conditionals_preserved` | Output contains `<!--[if mso]>` |
| 13 | `TestDocumentStructure` | `test_preheader_injected` | `preheader="Preview text"` → hidden div contains "Preview text" |
| 14 | `TestCaching` | `test_cache_hit_on_identical_compilation` | Compile same section twice → second is faster (cache hit), HTML identical |

**All tests use real component templates** from `email-templates/components/` (loaded via `COMPONENT_SEEDS`). No fabricated HTML. Use `hero-block` (has `headline`/`subtext`/`cta_url`/`cta_text` slots), `button` (has `cta_url`/`cta_text` slots), `divider` (no slots).

## Preflight Warnings

- `_extract_slots_from_html` in `file_loader.py:25` is private — import it or reimplement slot extraction (prefer re-using the `_DATA_SLOT_RE` pattern)
- `COMPONENT_SEEDS` calls `_build_all_seeds()` at import time — test isolation may need to mock or fixture the seed list
- lxml `fragment_fromstring()` can add wrapper `<div>` for multi-root fragments — use `fragments_fromstring()` or `document_fromstring()` as needed
- Component HTML may have nested `data-slot` elements (e.g., `cta_url` on `<a>` containing `<span data-slot="cta_text">`) — slot filling must handle parent/child slots correctly

## Security Checklist

No new endpoints in this task (pure library code). Security concerns:

| Check | Status |
|-------|--------|
| `HtmlSlot` content → `sanitize_component_html()` | In design |
| `TextSlot` content → `html.escape()` | In design |
| `ButtonSlot.href` → URL scheme whitelist (`http`/`https`/`mailto`/`tel`) | In design |
| `style_overrides` keys → already validated by Pydantic regex on `TreeSection` | Existing |
| No `eval()`, `exec()`, `subprocess` | N/A |
| No SQL injection surface | N/A |

## Verification

- [ ] `make check` passes
- [ ] `make types` — pyright errors ≤ 7 (baseline)
- [ ] Compile tree with 5 sections → valid email HTML with all slots filled
- [ ] `hero-block` component has correct `<img>` from `ImageSlot`
- [ ] Style override `{"background-color": "#FF0000"}` applied to root element
- [ ] `__custom__` section uses provided HTML
- [ ] XSS in `HtmlSlot` → sanitized
- [ ] Dark mode media query present
- [ ] MSO conditionals preserved
- [ ] Cache hit on second identical compilation
- [ ] 14 tests pass
