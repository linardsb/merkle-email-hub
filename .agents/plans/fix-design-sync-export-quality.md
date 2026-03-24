# Plan: Fix Design Sync Export Quality — 5 Issues

## Context

Design sync import pipeline produces email HTML with 5 quality issues visible in the exported output:

1. **Font-family not applied** — Design fonts don't reach the final HTML inline styles
2. **Email width 100%** — Content bleeds full-width instead of 600px constraint
3. **HTML nesting errors** — Redundant table nesting from converter → scaffolder handoff
4. **Footer uses `<p>` tags** — `sanitize_web_tags_for_email()` runs but scaffolder re-introduces them, or structured mode bypasses sanitization
5. **Placeholder images** — `via.placeholder.com` URLs survive into final output despite injection logic

### Root Cause Analysis

**Issue 1 (fonts):** The converter puts `font-family` in a `<style>` block (`converter_service.py:124`) which email clients strip. The body tag has no inline `font-family`. Typography in the scaffolder prompt is a descriptive text line, not an actionable inline-style instruction. Result: the LLM generates HTML without the design's fonts.

**Issue 2 (width):** `EMAIL_SKELETON` line 46 uses `style="margin:0 auto;max-width:600px;width:100%;"` but has NO `width="600"` HTML attribute. Many email clients (Outlook, Gmail) ignore `max-width` CSS but honor the `width` HTML attribute. Additionally, inner section tables from the converter use the design's pixel width (`node.width`) which may not be 600, creating width mismatches.

**Issue 3 (nesting):** `converter_service.py:113` wraps each frame in `<tr><td>\n{section_html}\n</td></tr>`. The frame itself already generates a `<table width="NNN">` via `node_to_email_html()`. Result: `outer-table > tr > td > section-table > tr > td > child-table` — three table levels before content. Inner section tables should use `width="100%"` to fill their container, not repeat the absolute pixel width.

**Issue 4 (footer p tags):** Two paths lead to `<p>` tags in output:
- **HTML mode:** Scaffolder LLM generates `<p>` tags; `sanitize_web_tags_for_email` converts them to `content<br><br>` but the result is bare text with `<br>` instead of properly structured `<table><tr><td>` content.
- **Structured mode:** `TemplateAssembler` fills golden template slots. Golden templates legitimately use `<p>` inside `<td>` (e.g., `hero_text.html`). But footer slot content from the design may have multi-line text that the LLM wraps in extra `<p>` tags.
- The prompt's instruction says "NEVER `<div>` or `<p>` for structure" but allows `<p>` for content — ambiguous. Need a stronger, explicit ban for design-sync context.

**Issue 5 (images):** The placeholder regex works correctly BUT the issue is upstream — the `url_pool` is empty when Strategy 3 runs. This happens when:
- Asset download silently failed (exception caught at `import_service.py:115-120`)
- OR no IMAGE nodes were detected (layout analyzer returns empty images list)
- OR the Scaffolder in HTML mode ignored the image URLs and generated new `<img>` tags with placeholder URLs, consuming all pool entries in Strategy 2 on empty-src tags that no longer match (LLM rewrote them)

The real fix: make the converter skeleton the primary image path (pre-fill before scaffolder) AND repeat image URLs in the post-scaffolder injection with the full URL list (not just unused ones).

## Files to Modify

| File | Change |
|------|--------|
| `app/design_sync/converter_service.py` | Fix `EMAIL_SKELETON` width; add inline body font-family; fix section table width |
| `app/design_sync/converter.py` | Fix frame table width for nested frames; propagate font-family to `<td>` wrappers |
| `app/design_sync/import_service.py` | Improve `_inject_asset_urls` to use full URL pool; strengthen sanitization order |
| `app/ai/agents/scaffolder/prompt.py` | Add explicit font-family inline instruction; strengthen no-p/div rule; repeat image URLs |
| `app/design_sync/tests/test_penpot_converter.py` | Tests for width, font, nesting fixes |
| `app/design_sync/tests/test_import_service.py` | Tests for image injection with full pool |

## Implementation Steps

### Step 1: Fix `EMAIL_SKELETON` width and inline body font (Issues 1 & 2)

**File:** `app/design_sync/converter_service.py`

**1a.** Add `width="600"` HTML attribute to main wrapper table AND add `font-family` to `<body>` inline style:

Replace the `EMAIL_SKELETON` constant (lines 26-54):

```python
EMAIL_SKELETON = """<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<!--[if mso]>
<noscript><xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml></noscript>
<![endif]-->
{style_block}
</head>
<body style="margin:0;padding:0;word-spacing:normal;background-color:{bg_color};color:{text_color};font-family:{body_font};">
<div role="article" aria-roledescription="email" lang="en" style="text-size-adjust:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<!--[if mso]>
<table role="presentation" width="600" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td>
<![endif]-->
<table role="presentation" width="600" style="margin:0 auto;max-width:600px;width:100%;" cellpadding="0" cellspacing="0" border="0">
{sections}
</table>
<!--[if mso]>
</td></tr></table>
<![endif]-->
</div>
</body>
</html>"""
```

Changes:
- Added `width="600"` HTML attribute to main table (line with `{sections}`)
- Added `font-family:{body_font};` to `<body>` inline style

**1b.** Update the `convert()` method to pass `body_font` to the skeleton:

In `convert()` method, after line 123 (`safe_body_font = ...`), update the `format()` call:

```python
result_html = EMAIL_SKELETON.format(
    style_block=style_block,
    bg_color=bg_color,
    text_color=text_color,
    body_font=safe_body_font or "Arial, Helvetica, sans-serif",
    sections=sections_html,
)
```

### Step 2: Fix section table widths (Issues 2 & 3)

**File:** `app/design_sync/converter.py`

In `node_to_email_html()`, for FRAME/GROUP/COMPONENT/INSTANCE nodes (line 261):

Currently:
```python
width_attr = f' width="{int(node.width)}"' if node.width else ""
```

Change to: use `width="100%"` for nested frames (frames that have a parent), `width="600"` only for top-level frames:

```python
# Nested frames use 100% to fill parent; top-level would use 600 but
# the converter_service wraps them in <tr><td>, so 100% is correct.
width_attr = ' width="100%"'
```

This prevents inner section tables from competing with the 600px wrapper. All sections should fill their parent container.

### Step 3: Propagate font-family to frame `<td>` wrappers (Issue 1)

**File:** `app/design_sync/converter.py`

In `node_to_email_html()`, when wrapping non-text children in `<td>` (lines 309-311), AND for text nodes, ensure the parent's font context propagates.

Add a `parent_font` parameter to `node_to_email_html`:

```python
def node_to_email_html(
    node: DesignNode,
    *,
    indent: int = 0,
    props_map: dict[str, _NodeProps] | None = None,
    parent_bg: str | None = None,
    parent_font: str | None = None,  # NEW
) -> str:
```

In the TEXT node handler (line 221), use `parent_font` as fallback:

```python
if node.type == DesignNodeType.TEXT:
    content = html.escape(node.text_content or "")
    font_family = parent_font or "Arial,Helvetica,sans-serif"
    # ... rest of font handling from props
```

In the FRAME handler, extract the effective font from props and pass it to children:

```python
# After props extraction (around line 276):
effective_font = parent_font
if props and props.font_family:
    safe_family = _sanitize_css_value(props.font_family)
    if safe_family:
        effective_font = f"{safe_family},Arial,Helvetica,sans-serif"
```

Pass `parent_font=effective_font` in the recursive call (line 302-306):

```python
child_html = node_to_email_html(
    child,
    indent=indent + 2,
    props_map=props_map,
    parent_bg=effective_bg,
    parent_font=effective_font,
)
```

Also add `font-family` to `<td>` wrapper elements (lines 309-311) when font context is available:

```python
if child.type != DesignNodeType.TEXT:
    font_style = f' style="font-family:{effective_font};"' if effective_font else ""
    lines.append(f"{pad}    <td{font_style}>")
    lines.append(child_html)
    lines.append(f"{pad}    </td>")
```

### Step 4: Strengthen scaffolder prompt for design-sync context (Issues 1, 4, 5)

**File:** `app/ai/agents/scaffolder/prompt.py`

**4a.** In `build_design_context_section()`, strengthen the structural enforcement block (line 98-105):

Replace:
```python
parts.append(
    "**CRITICAL — Email HTML structure requirements:**\n"
    '- Use `<table role="presentation">` for ALL layout — NEVER `<div>` or `<p>` for structure\n'
    "- Every section: `<table>` > `<tr>` > `<td>` > content\n"
    "- Multi-column: MSO ghost table pattern with `display:inline-block` divs\n"
    "- All styles inline on every element\n"
    "- MSO conditional wrappers around the 600px container\n"
)
```

With:
```python
parts.append(
    "**CRITICAL — Email HTML structure requirements:**\n"
    '- Use `<table role="presentation">` for ALL layout — NEVER `<div>` or `<p>` for structure\n'
    "- NEVER use `<p>` tags anywhere — use `<td>` with inline styles for ALL text content\n"
    "- NEVER use `<div>` tags for layout — only for `role=\"article\"` wrapper and MSO hybrid columns\n"
    "- Every section: `<table>` > `<tr>` > `<td>` > content (text directly in `<td>`, no `<p>` wrapper)\n"
    "- Multi-column: MSO ghost table pattern with `display:inline-block` divs\n"
    "- All styles inline on every element including `font-family` on EVERY `<td>` and heading\n"
    "- MSO conditional wrappers around the 600px container\n"
    "- Main email container: `width=\"600\"` HTML attribute + `max-width:600px` CSS\n"
)
```

**4b.** In the typography section (lines 164-171), add explicit font-family inline instruction:

Replace:
```python
typography = tokens.get("typography", [])
if isinstance(typography, list) and typography:
    typo_dicts: list[dict[str, object]] = [t for t in typography if isinstance(t, dict)]
    font_list = ", ".join(
        f"{t.get('name', '?')}: {t.get('family', '?')} {t.get('size', '?')}px"
        for t in typo_dicts
    )
    parts.append(f"**Typography:** {font_list}")
```

With:
```python
typography = tokens.get("typography", [])
if isinstance(typography, list) and typography:
    typo_dicts: list[dict[str, object]] = [t for t in typography if isinstance(t, dict)]
    font_list = ", ".join(
        f"{t.get('name', '?')}: {t.get('family', '?')} {t.get('size', '?')}px"
        for t in typo_dicts
    )
    parts.append(f"**Typography:** {font_list}")
    # Extract primary body and heading fonts for explicit inline instruction
    body_fonts = [t for t in typo_dicts if any(
        kw in str(t.get("name", "")).lower() for kw in ("body", "text", "paragraph", "regular")
    )]
    heading_fonts = [t for t in typo_dicts if any(
        kw in str(t.get("name", "")).lower() for kw in ("heading", "title", "h1", "h2")
    )]
    body_family = str(body_fonts[0].get("family", "")) if body_fonts else ""
    heading_family = str(heading_fonts[0].get("family", "")) if heading_fonts else ""
    if body_family or heading_family:
        parts.append(
            "\n**INLINE FONT REQUIREMENT — Apply these font-family stacks on EVERY element:**"
        )
        if body_family:
            stack = f"{body_family}, Arial, Helvetica, sans-serif" if "," not in body_family else body_family
            parts.append(f'- Body text `<td>`: `font-family: {stack};`')
        if heading_family:
            stack = f"{heading_family}, Arial, Helvetica, sans-serif" if "," not in heading_family else heading_family
            parts.append(f'- Headings `<h1>`, `<h2>`: `font-family: {stack};`')
        parts.append("- Do NOT rely on `<style>` blocks or inheritance — inline on every element")
```

### Step 5: Fix image URL injection to use full pool (Issue 5)

**File:** `app/design_sync/import_service.py`

The current `_inject_asset_urls` Strategy 2 pops URLs from `url_pool` for empty `src=""` tags, which depletes the pool before Strategy 3 (placeholder replacement) runs.

**5a.** Change Strategy 3 to use the FULL `image_urls` values, not just leftover `url_pool`:

In `_inject_asset_urls()`, after Strategy 1 (line 438), change the pool construction and Strategy 3:

```python
# Build pool of unused asset URLs for positional assignment
url_pool = [u for u in image_urls.values() if u not in used_urls]

# Strategy 2: fill remaining empty src="" attributes
if url_pool:
    pool_iter = iter(list(url_pool))  # copy for Strategy 2

    def _fill_empty(m: re.Match[str]) -> str:
        nonlocal pool_iter
        try:
            url = next(pool_iter)
            return m.group(0).replace('src=""', f'src="{url}"', 1)
        except StopIteration:
            return m.group(0)

    html = re.sub(r'<img\s[^>]*src=""[^>]*/?>', _fill_empty, html)

# Strategy 3: replace common placeholder URLs — use FULL url list
# (not just remaining pool) because LLM may have generated new
# <img> tags with placeholder URLs that weren't in the skeleton
all_urls = list(image_urls.values())
if all_urls:
    _PLACEHOLDER_RE = re.compile(
        r'src="https?://(?:'
        r"[\w.-]*placeholder[\w.-]*"
        r"|placehold\.co"
        r"|dummyimage\.com"
        r"|picsum\.photos"
        r"|loremflickr\.com"
        r"|fakeimg\.pl"
        r"|lorempixel\.com"
        r')[^"]*"'
    )
    url_idx = [0]  # mutable counter for closure

    def _fill_placeholder(m: re.Match[str]) -> str:
        if url_idx[0] < len(all_urls):
            url = all_urls[url_idx[0] % len(all_urls)]
            url_idx[0] += 1
            return f'src="{url}"'
        return m.group(0)

    html = _PLACEHOLDER_RE.sub(_fill_placeholder, html)
```

Key change: Strategy 3 cycles through ALL asset URLs (with modulo wrap) instead of only unused ones. This ensures every placeholder URL gets replaced even if the pool was depleted by Strategy 2.

**5b.** Add logging when no image URLs are available for injection:

In `run_conversion()`, after building `design_context` (line 138), add:

```python
image_urls = design_context.get("image_urls", {})
if not image_urls:
    logger.warning(
        "design_sync.no_image_urls_for_scaffolder",
        import_id=import_id,
        asset_response_exists=asset_response is not None,
    )
```

### Step 6: Ensure sanitization runs LAST (Issue 4)

**File:** `app/design_sync/import_service.py`

The current order is:
```
_inject_asset_urls → _sanitize_email_html → _fix_orphaned_footer
```

The `_fix_orphaned_footer` can introduce content that hasn't been sanitized. Move sanitization to run AFTER orphaned footer fix:

Change the order in `run_conversion()` (lines 198-213):

```python
# 6.5 Post-process: inject design asset URLs
image_urls = design_context.get("image_urls")
if isinstance(image_urls, dict) and image_urls:
    scaffolder_response = self._inject_asset_urls(
        scaffolder_response, image_urls,
    )

# 6.6 Fix orphaned footer content outside main wrapper table
scaffolder_response = self._fix_orphaned_footer(scaffolder_response)

# 6.7 Sanitize web-only tags and fix text contrast (LAST — catches all prior steps)
scaffolder_response = self._sanitize_email_html(scaffolder_response)
```

### Step 7: Tests

**File:** `app/design_sync/tests/test_penpot_converter.py`

Add tests:

| Test | Verifies |
|------|----------|
| `test_frame_table_width_100_percent` | `node_to_email_html()` for FRAME produces `width="100%"` not pixel width |
| `test_font_family_propagates_to_children` | Parent frame font reaches child TEXT `<td>` via `parent_font` |
| `test_font_family_on_td_wrapper` | Non-text child `<td>` gets `style="font-family:..."` when parent has font |
| `test_email_skeleton_has_width_600` | `EMAIL_SKELETON` formatted output contains `width="600"` on main table |
| `test_email_skeleton_body_has_inline_font` | `<body>` tag includes `font-family:` in inline style |

**File:** `app/design_sync/tests/test_import_service.py`

Add tests:

| Test | Verifies |
|------|----------|
| `test_inject_asset_urls_placeholder_uses_full_pool` | Strategy 3 replaces `via.placeholder.com` URLs even when Strategy 2 consumed pool |
| `test_sanitize_runs_after_orphan_fix` | Orphaned footer content with `<p>` tags gets sanitized |
| `test_placeholder_cycling` | Multiple placeholder URLs cycle through available assets |

Use minimal table-based HTML snippets for unit tests, following existing test patterns in those files.

## Security Checklist

No new endpoints. All changes are internal pipeline processing:
- `parent_font` parameter: sanitized through `_sanitize_css_value()` before use in inline styles
- `width="600"` is a static constant, no injection risk
- `body_font` in skeleton: sanitized via `_sanitize_css_value()` before template interpolation
- Image URL injection uses existing URL pool from trusted design API responses
- Font family extraction from prompt context uses string formatting, no user-controlled input reaches CSS directly

## Verification

- [ ] `make check` passes (lint + types + tests + security)
- [ ] Import design → font-family appears inline on every `<td>` and heading in output HTML
- [ ] Import design → main wrapper table has `width="600"` HTML attribute
- [ ] Import design → no triple-nested empty `<table>` structures
- [ ] Import design → no `<p>` tags in footer or body sections
- [ ] Import design → actual asset URLs from `/api/v1/design-sync/assets/` in all `<img>` tags
- [ ] Existing tests in `test_penpot_converter.py`, `test_import_service.py`, `test_layout_analyzer.py` pass
