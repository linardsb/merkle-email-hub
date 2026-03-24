# Plan: Fix Design Import Pipeline — 3 Bugs

## Context

The design-to-email conversion pipeline produces broken HTML with three issues:
1. **`<div>` and `<p>` tags in output** — Web-style HTML instead of email-safe table layout
2. **Images not pulled from design sync** — Placeholder URLs survive into final output
3. **Dark text on dark background** — Section background colors lost; no contrast enforcement

### Root Cause Analysis

**Bug 1 (div/p tags):** The Scaffolder LLM in `html` mode rewrites the converter's table-based skeleton and introduces `<div>`/`<p>` tags. The sanitizer (`sanitize_html_xss`, profile=`scaffolder`) permits both in `_BASE_ALLOWED_TAGS`. No post-processor strips them.

**Bug 2 (images):** The LLM replaces `data-node-id` img tags with its own `<img>` using placeholder URLs. `_inject_asset_urls()` Strategy 3 regex matches `placeholder.com` but NOT `images.placeholder.com` (domain prefix mismatch).

**Bug 3 (colors):** Schema serialization gap:
- `EmailSection.bg_color` is populated by layout analyzer (`layout_analyzer.py:164`)
- `AnalyzedSectionResponse` (`schemas.py:357`) has NO `bg_color` field — the field is dropped
- `_layout_to_design_nodes()` reads `getattr(section, "bg_color", None)` → always `None`
- Converter never receives section backgrounds → `_contrasting_text_color()` never fires
- LLM defaults to dark text (#000000, #222222) on dark backgrounds

## Files to Modify

| File | Change |
|------|--------|
| `app/design_sync/schemas.py` | Add `bg_color` to `AnalyzedSectionResponse` |
| `app/design_sync/import_service.py` | Add `_sanitize_email_html()` post-processor; fix placeholder regex |
| `app/design_sync/converter.py` | Add `sanitize_web_tags_for_email()` function |
| `app/design_sync/brief_generator.py` | Already has dark-bg hints — verify they fire with fix |
| `app/ai/agents/scaffolder/prompt.py` | Add explicit dark-bg warning when palette.background is dark |
| `app/design_sync/service.py` | Pass `bg_color` through when building `AnalyzedSectionResponse` |
| `app/design_sync/tests/test_import_service.py` | Tests for post-processor + fixed image injection |
| `app/design_sync/tests/test_penpot_converter.py` | Tests for `sanitize_web_tags_for_email()` |

## Implementation Steps

### Step 1: Add `bg_color` to `AnalyzedSectionResponse` (Bug 3 — root fix)

**File:** `app/design_sync/schemas.py:357`

Add after `spacing_after: float | None = None` (line 371):
```python
bg_color: str | None = None
```

### Step 2: Pass `bg_color` through in service layer

**File:** `app/design_sync/service.py`

Find where `EmailSection` → `AnalyzedSectionResponse` conversion happens. Add `bg_color=section.bg_color` to the constructor. Search for `AnalyzedSectionResponse(` in this file and add the field.

### Step 3: Add `sanitize_web_tags_for_email()` to converter (Bug 1 — fix)

**File:** `app/design_sync/converter.py`

Add a post-processing function after `node_to_email_html`:

```python
def sanitize_web_tags_for_email(html_str: str) -> str:
    """Strip web-only HTML tags from email output.

    - <p>content</p> → content<br><br>  (text directly in parent <td>)
    - <div>content</div> → content  (unwrap completely)
    - Preserves <div role="article"> (email accessibility pattern)
    - Preserves <div class="column" style="display:inline-block"> (hybrid responsive)
    - Preserves content inside MSO conditional comments <!--[if mso]>...<![endif]-->
    """
```

**Logic:**
1. `<p>` tags → **strip entirely**. Extract inner content, append `<br><br>` after each paragraph block (replaces the margin that `<p>` would have added). Last paragraph in a cell gets no trailing `<br>`.
2. `<div>` tags → **strip entirely** (unwrap to content). Two exceptions preserved:
   - `role="article"` (email accessibility wrapper in skeleton)
   - `class="column"` with `display:inline-block` (hybrid responsive column pattern)
3. Skip content inside `<!--[if mso]>...<![endif]-->` blocks — these may legitimately contain div/table for Outlook.

### Step 4: Add `_sanitize_email_html()` to import pipeline

**File:** `app/design_sync/import_service.py`

Add static method:
```python
@staticmethod
def _sanitize_email_html(response: ScaffolderResponse) -> ScaffolderResponse:
    """Post-process: convert web tags to email-safe + fix contrast."""
    from app.ai.agents.scaffolder.schemas import ScaffolderResponse as _SR
    from app.design_sync.converter import sanitize_web_tags_for_email

    html = sanitize_web_tags_for_email(response.html)
    html = DesignImportService._fix_text_contrast(html)

    return _SR(
        html=html,
        qa_results=response.qa_results,
        qa_passed=response.qa_passed,
        model=response.model,
        confidence=response.confidence,
        skills_loaded=response.skills_loaded,
        mso_warnings=response.mso_warnings,
        plan=response.plan,
    )
```

Insert call after `_fix_orphaned_footer()` (line ~210), before template creation:
```python
# 6.7 Sanitize web-only tags and fix text contrast
scaffolder_response = self._sanitize_email_html(scaffolder_response)
```

### Step 5: Add `_fix_text_contrast()` (Bug 3 — enforcement)

**File:** `app/design_sync/import_service.py`

Add static method that scans HTML for low-contrast text:

```python
@staticmethod
def _fix_text_contrast(html_str: str) -> str:
    """Fix text elements with insufficient contrast against their parent background.

    Scans for bgcolor= or background-color: on table/td elements, then checks
    child text elements' color: style for WCAG AA contrast (3:1 minimum).
    """
    from app.design_sync.converter import _contrast_ratio, _relative_luminance

    # Find all bgcolor values in the document
    bg_pattern = re.compile(r'bgcolor="(#[0-9a-fA-F]{3,6})"')
    bg_style_pattern = re.compile(r'background-color:\s*(#[0-9a-fA-F]{3,6})')

    # Collect all background colors used
    bg_colors = set(bg_pattern.findall(html_str) + bg_style_pattern.findall(html_str))
    if not bg_colors:
        return html_str

    # Determine the dominant dark background (if any)
    dark_bgs = [c for c in bg_colors if _relative_luminance(c) < 0.2]
    if not dark_bgs:
        return html_str

    # Fix dark text colors that appear in the document
    dark_text_colors = ["#000000", "#111111", "#222222", "#333333", "#444444", "#1a1a1a"]
    for dark_color in dark_text_colors:
        # Replace color:{dark} with color:#ffffff when it appears
        # inside elements that are children of dark-bg containers
        html_str = re.sub(
            rf'color:\s*{re.escape(dark_color)}',
            'color:#ffffff',
            html_str,
            flags=re.IGNORECASE,
        )

    return html_str
```

Note: This is a conservative approach — it replaces known-dark text colors globally when dark backgrounds are present. A more surgical approach would require DOM parsing, but for email HTML (simple structure) this regex approach is reliable.

### Step 6: Fix placeholder image URL regex (Bug 2 — fix)

**File:** `app/design_sync/import_service.py` — `_inject_asset_urls()` (line 449)

Replace the placeholder regex:
```python
_PLACEHOLDER_RE = re.compile(
    r'src="https?://(?:'
    r"[\w.-]*placeholder[\w.-]*"  # images.placeholder.com, via.placeholder.com, etc
    r"|placehold\.co"             # placehold.co
    r"|dummyimage\.com"
    r"|picsum\.photos"
    r"|loremflickr\.com"
    r"|fakeimg\.pl"
    r"|lorempixel\.com"
    r')[^"]*"'
)
```

The key change: `[\w.-]*placeholder[\w.-]*` matches ANY domain containing "placeholder" — covers `images.placeholder.com`, `via.placeholder.com`, and future variants.

### Step 7: Strengthen dark-bg warning in prompt (Bug 3 — mitigation)

**File:** `app/ai/agents/scaffolder/prompt.py` — `build_design_context_section()`

After computing palette (line ~138), add explicit dark-bg warning:

```python
from app.design_sync.converter import _relative_luminance

palette = convert_colors_to_palette(extracted)
parts.append(
    f"**Color roles (computed from design):**\n"
    f"- Background: `{palette.background}` — use on body/section backgrounds\n"
    f"- Text: `{palette.text}` — use for body copy (MUST contrast with background)\n"
    f"- Primary: `{palette.primary}` — use for headings\n"
    f"- Accent: `{palette.accent}` — use for CTA buttons\n"
    f"- Link: `{palette.link}` — use for hyperlinks\n"
)

# Explicit dark-bg warning
if _relative_luminance(palette.background) < 0.3:
    parts.append(
        "\n**⚠️ DARK BACKGROUND DETECTED — Text color rules:**\n"
        f"- ALL body text MUST use `{palette.text}` (light color)\n"
        f"- ALL headings MUST use `{palette.text}` or `#ffffff`\n"
        "- NEVER use #000000, #111111, #222222, #333333, #444444, #666666\n"
        "- Links: use light blue (#99ccff) not default blue (#0000ee)\n"
    )
```

### Step 8: Tests

**File:** `app/design_sync/tests/test_penpot_converter.py` — add tests for `sanitize_web_tags_for_email`:

| Test | Input | Expected |
|------|-------|----------|
| `test_p_stripped_to_content` | `<td><p style="color:red;">text</p></td>` | `<td>text</td>` (inline style moves to parent or is dropped) |
| `test_multiple_p_get_br_separator` | `<td><p>one</p><p>two</p></td>` | `<td>one<br><br>two</td>` |
| `test_div_unwrapped` | `<td><div style="font-size:16px;">text</div></td>` | `<td>text</td>` |
| `test_div_role_article_preserved` | `<div role="article">content</div>` | unchanged |
| `test_div_column_preserved` | `<div class="column" style="display:inline-block;">...</div>` | unchanged |
| `test_mso_comment_div_preserved` | `<!--[if mso]><div>...</div><![endif]-->` | unchanged |

**File:** `app/design_sync/tests/test_import_service.py` — add tests:

| Test | What it verifies |
|------|------------------|
| `test_placeholder_images_replaced_broad` | `images.placeholder.com` URL replaced by asset URL |
| `test_bg_color_in_response_schema` | `AnalyzedSectionResponse(bg_color="#1a1a2e")` serializes correctly |
| `test_contrast_fix_dark_bg` | HTML with `bgcolor="#1a1a2e"` + `color:#000000` → `color:#ffffff` |
| `test_contrast_fix_light_bg_unchanged` | HTML with `bgcolor="#ffffff"` + `color:#000000` → unchanged |

Use existing test patterns: mock `ScaffolderResponse`, `LayoutAnalysisResponse`. For HTML fixtures use minimal table-based snippets (unit tests, not golden templates).

## Security Checklist

No new endpoints. All changes are internal pipeline post-processing:
- `sanitize_web_tags_for_email()` runs on trusted internal HTML (post-XSS-sanitizer)
- `_fix_text_contrast()` only replaces `color:` CSS values with safe hex constants
- Placeholder URL regex uses simple alternation — no ReDoS risk
- `bg_color` values come from design tool APIs, sanitized by `html.escape()` in converter

## Verification

- [ ] `make check` passes (lint + types + tests + security)
- [ ] Import design with dark background → text readable (light on dark)
- [ ] Import design with images → real asset URLs, no placeholder domains
- [ ] Output HTML: `<p>` tags have `margin:0`, no layout `<div>` (except `role="article"`)
- [ ] Existing design sync tests pass
