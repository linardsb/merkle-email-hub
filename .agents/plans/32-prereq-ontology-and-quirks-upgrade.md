# Plan: Phase 32 Prerequisites — Ontology & Quirks Upgrade

## Context

Before Phase 32 (Agent Email Rendering Intelligence) ships, four gaps need closing:

1. **New Outlook for Windows** (Chromium-based, codenamed "Monarch") is lumped under `outlook_web` in the ontology. Microsoft is deprecating classic Outlook in October 2026 — this needs its own profile now so support matrix entries can diverge as Microsoft rolls out updates.
2. **Samsung foldable** coverage in `samsung-mail.md` is two sentences. Missing: Flex Mode, One UI version differences, component-level testing guidance.
3. **Consolidated New Outlook quirks seed** — references are scattered across 5+ files with no dedicated quirks document.
4. **Skill file trimming prep** — L3 files that duplicate client facts should get deprecation headers and priority demotion ahead of the 32.4 lookup tool, so the transition is gradual.

## Files to Create/Modify

### New Files
- `app/knowledge/data/seeds/client_quirks/outlook-new-windows.md` — dedicated quirks seed for New Outlook

### Modified Files
- `app/knowledge/ontology/data/clients.yaml` — add `outlook_new_win` client
- `app/knowledge/ontology/data/support_matrix.yaml` — add `outlook_new_win` entries (copy from `outlook_web` with overrides)
- `app/knowledge/ontology/sync/mapper.py` — add CLIENT_MAP entry for New Outlook
- `app/knowledge/data/seed_manifest.py` — register new quirks seed
- `app/knowledge/data/seeds/client_quirks/samsung-mail.md` — expand foldable section
- `app/knowledge/data/seeds/client_quirks/outlook-web.md` — add cross-reference to new `outlook-new-windows.md`
- `app/knowledge/ontology/tests/test_registry.py` — update client count assertion, add `outlook_new_win` test
- `app/knowledge/ontology/sync/tests/test_mapper.py` — add New Outlook mapping test
- `app/knowledge/tests/test_seed.py` — update domain count assertion (7 client_quirks)
- `app/ai/agents/dark_mode/skills/client_behavior.md` — add deprecation header
- `app/ai/agents/outlook_fixer/skills/mso_conditionals.md` — add deprecation header
- `app/ai/agents/scaffolder/skills/client_compatibility.md` — add deprecation header
- `app/ai/agents/code_reviewer/skills/css_support_matrix.md` — add deprecation header

## Implementation Steps

### Step 1: Add `outlook_new_win` to `clients.yaml`

Insert after the `outlook_web` entry (after line 116):

```yaml
  - id: outlook_new_win
    name: "New Outlook for Windows"
    family: outlook
    platform: windows
    engine: custom
    market_share: 5.0
    notes: >-
      Chromium-based desktop app replacing classic Outlook for Windows (Microsoft
      deprecating classic Outlook October 2026). Shares the Outlook.com/OWA
      rendering engine — NOT the Word engine. Supports CSS background images,
      border-radius, and max-width (unlike Word-based Outlook). Strips flexbox,
      grid, position, and float identically to outlook_web. Key differences from
      outlook_web: resizable desktop window (not browser tab) creates different
      viewport behavior, local image cache + proxy hybrid for image handling,
      and OS-level dark mode integration via Windows system settings. MSO
      conditional comments are ignored — do NOT wrap layout in <!--[if mso]>
      blocks for this client. Test alongside classic Outlook 365 during the
      transition period.
    tags: [desktop, enterprise, transition]
```

### Step 2: Add `outlook_new_win` support matrix entries

The support matrix uses "default is FULL" — only `none` and `partial` entries are recorded. `outlook_new_win` shares the same rendering engine as `outlook_web`, so copy all `outlook_web` entries and change `client_id` to `outlook_new_win`.

First, add `outlook_new_win` to the header comment (line 9):

```yaml
#   outlook_2016_win, outlook_2019_win, outlook_365_win, outlook_mac,
#   outlook_ios, outlook_android, outlook_web, outlook_new_win,
```

Then, for every `outlook_web` entry in `support_matrix.yaml`, duplicate it with `client_id: outlook_new_win`. Search for all `client_id: outlook_web` entries and duplicate them. The notes should say "Shares outlook_web rendering engine" instead of repeating the OWA-specific note.

Use this approach:
1. `grep -n "client_id: outlook_web" support_matrix.yaml` to find all entries
2. For each entry, copy the block (property_id, client_id, level, notes, workaround) and replace `outlook_web` → `outlook_new_win`
3. Place duplicate entries immediately after their `outlook_web` counterpart

### Step 3: Update caniemail sync mapper

In `app/knowledge/ontology/sync/mapper.py`, add to `CLIENT_MAP` (line 14):

```python
    ("outlook", "outlook-com"): "outlook_com",
    # Add this new entry:
    ("new-outlook", "windows"): "outlook_new_win",
```

Note: Can I Email may not have a "new-outlook" family yet. This entry is forward-looking — when/if they add it, the sync will map correctly. The existing `("outlook", "windows")` continues mapping to `outlook_2019_win` for the classic Word-based client.

### Step 4: Create `outlook-new-windows.md` quirks seed

Create `app/knowledge/data/seeds/client_quirks/outlook-new-windows.md` following the structure pattern from existing quirks files (heading, overview, sections with code examples, key takeaways).

Structure:

```markdown
# New Outlook for Windows Rendering Quirks

## Overview

New Outlook for Windows (codenamed "Monarch") is Microsoft's Chromium-based
replacement for classic Outlook. Unlike Outlook 2016/2019/365 which use the
Word rendering engine, New Outlook shares the Outlook.com/OWA rendering engine.
This means dramatically different CSS support, no MSO conditional processing,
and no VML rendering.

Developers must test both classic and New Outlook during the transition
(classic Outlook deprecation: October 2026). Code that relies on MSO
conditionals or VML will be invisible in New Outlook.

## Rendering Engine Differences

| Feature | Classic Outlook (Word) | New Outlook (Chromium) |
|---|---|---|
| MSO Conditionals | Processed | Ignored (hidden) |
| VML Shapes | Rendered | Ignored |
| border-radius | Not supported | Supported |
| background-image (CSS) | Not supported | Supported |
| max-width | Ignored | Supported |
| Media queries | Not supported | Not supported (same as OWA) |
| Flexbox | Not supported | Not supported (stripped) |
| CSS Grid | Not supported | Not supported (stripped) |

## CSS Sanitization

[Same sanitization as outlook_web — document the pipeline: class/ID renaming,
style block stripping, safe property whitelist. Reference outlook-web.md for
full details, focus on differences here.]

## Dark Mode Behavior

New Outlook respects Windows system dark mode settings. Behavior:
- Applies forced color inversion on light backgrounds
- `prefers-color-scheme: dark` media query NOT supported (no media queries in OWA engine)
- Use `data-ogsc` and `data-ogsb` attribute selectors for dark mode control
- `[data-ogsc] .dark-text { color: #ffffff !important; }` pattern works
- Images are NOT auto-inverted (unlike some mobile clients)
- Background colors may be forcibly changed — use `data-ogsb` to override

## Viewport and Layout

Unlike Outlook.com in a browser tab, New Outlook runs as a resizable desktop
window:
- Window can be resized from ~320px to full screen width
- No media query support — use fluid table layouts
- `max-width: 600px` on wrapper table is reliable
- `width: 100%` with `max-width` provides fluid behavior
- Desktop window DPI scaling handled by Chromium (no Word DPI bugs)

## Migration from Classic Outlook

For codebases with heavy MSO conditional usage:
- MSO conditionals (`<!--[if mso]>...<![endif]-->`) are completely ignored — content inside is hidden
- VML backgrounds/buttons must have CSS fallbacks visible without conditionals
- Ghost table pattern still needed for classic Outlook but invisible in New Outlook — ensure the non-MSO content path renders correctly standalone
- `mso-` prefixed CSS properties are silently ignored

## Image Handling

- External images: loaded by default (no click-to-load prompt)
- Image proxy: hybrid local cache + Microsoft proxy
- Tracking pixels: function normally
- `display: block` on images: recommended (prevents gap bug)
- SVG: partial support (inline SVG stripped, `<img src="*.svg">` works)

## Key Takeaways

- New Outlook uses Chromium, NOT Word — treat it like Outlook.com, not like Outlook 365
- MSO conditionals and VML are invisible — ensure non-MSO fallback content renders correctly
- No media query support — use fluid tables for responsive design
- Dark mode via data-ogsc/data-ogsb attributes (no prefers-color-scheme)
- CSS sanitization identical to Outlook.com/OWA
- Test alongside classic Outlook during transition (deprecation October 2026)
- Rapidly growing market share as Microsoft forces migration
```

### Step 5: Expand Samsung foldable coverage in `samsung-mail.md`

Replace the single-sentence foldable paragraph (line 95) with a comprehensive section. Insert after line 93 (`</table>`) and replace the existing line 95:

```markdown
### Foldable Device Behavior (Galaxy Z Fold / Z Flip)

Samsung foldable devices present unique viewport challenges for email rendering:

**Galaxy Z Fold (unfolded → folded):**
- Unfolded inner display: ~717px CSS width (varies by model)
- Folded cover screen: ~280px CSS width
- Transition between states triggers a viewport resize — emails re-render live
- Content must adapt fluidly between 280px and 717px without media queries as a safety net

**Galaxy Z Flip:**
- Unfolded: standard ~360px mobile viewport
- Flex Mode (half-folded): viewport splits into two halves (~360px × ~320px visible area)
- Samsung Mail does NOT reliably reflow emails in Flex Mode — content may be clipped

**One UI version differences:**
- One UI 5.x (Android 13): viewport reporting is inconsistent; some versions report physical pixels instead of CSS pixels
- One UI 6.x (Android 14): improved viewport reporting; `meta viewport` tag respected more reliably
- One UI 7.x (Android 15): experimental foldable-aware CSS features in Samsung Internet but NOT in Samsung Mail's WebView

**Recommended approach:**

```html
<!-- Fluid wrapper that works across all fold states -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width: 600px; min-width: 280px; margin: 0 auto;">
  <tr>
    <td style="padding: 0 16px; width: 100%;">
      <!-- Content adapts between 280px and 600px+ -->
    </td>
  </tr>
</table>
```

- NEVER use fixed-width tables (e.g., `width="600"`) — these overflow on folded screens
- Use `max-width` + `width: 100%` for fluid behavior
- Images: use `max-width: 100%; height: auto;` to prevent overflow on narrow fold states
- Test on both folded and unfolded states if Samsung is >5% of your audience
```

### Step 6: Add cross-reference in `outlook-web.md`

Add a note at the end of the Overview section (after line 7):

```markdown
> **See also:** [outlook-new-windows.md](outlook-new-windows.md) for the "New Outlook" desktop app, which shares this rendering engine but has desktop-specific viewport and dark mode behavior.
```

### Step 7: Register new seed in `seed_manifest.py`

Add after the `outlook-web.md` entry (after line 168):

```python
    SeedEntry(
        filename="client_quirks/outlook-new-windows.md",
        domain="client_quirks",
        title="New Outlook for Windows Rendering Quirks",
        description="Chromium-based New Outlook: MSO conditional invisibility, CSS sanitization, dark mode via data-ogsc/ogsb, viewport behavior, migration from classic Outlook.",
        tags=["outlook", "new-outlook", "chromium", "dark-mode", "quirks"],
    ),
```

### Step 8: Update test assertions

**`app/knowledge/ontology/tests/test_registry.py`:**
- Line 19: change `assert len(self.registry.clients) >= 25` → `>= 26`
- Line 51: change `assert len(ids) >= 25` → `>= 26`
- Add test in `TestClientIndex`:
  ```python
  def test_new_outlook_client(self) -> None:
      client = self.registry.get_client("outlook_new_win")
      assert client is not None
      assert client.engine == ClientEngine.CUSTOM
      assert client.family == "outlook"
      assert client.platform == "windows"
  ```

**`app/knowledge/ontology/sync/tests/test_mapper.py`:**
- Add test for the new CLIENT_MAP entry:
  ```python
  def test_resolve_new_outlook_windows(self) -> None:
      assert resolve_client_id("new-outlook", "windows") == "outlook_new_win"
  ```

**`app/knowledge/tests/test_seed.py`:**
- Update `test_domain_counts` (line 46) to expect 7 `client_quirks` entries instead of 6.

### Step 9: Add deprecation headers to L3 client-fact skill files

For each of these files, prepend a deprecation notice at the top (after any existing front matter). Also change `priority` to `3` in front matter if present, or add front matter with `priority: 3`:

**Files to update:**

1. `app/ai/agents/dark_mode/skills/client_behavior.md`
2. `app/ai/agents/outlook_fixer/skills/mso_conditionals.md`
3. `app/ai/agents/scaffolder/skills/client_compatibility.md`
4. `app/ai/agents/code_reviewer/skills/css_support_matrix.md`

**Deprecation header to add** (after front matter `---` block):

```markdown
> **Deprecation Notice (Phase 32 prep):** Client-specific facts in this file
> will be superseded by the centralized ClientMatrix (Phase 32.1) and the
> `lookup_client_support` tool (Phase 32.4). This file is retained as a
> fallback reference. Priority demoted to 3 (supplementary) — only loaded
> when token budget allows.
```

**Front matter change:** If the file has `priority: 2` (or no priority), change to `priority: 3`. This ensures `should_load_skill()` in `skill_loader.py` only loads these files when budget capacity is above 70%.

### Step 10: Verify

Run the full check suite:

```bash
make check
```

This runs lint, types, tests, and security checks. Specific areas to verify:

- [ ] `make test` passes — especially `test_registry.py`, `test_mapper.py`, `test_seed.py`
- [ ] `make types` passes — no type errors from new YAML entries
- [ ] `make lint` passes — seed manifest formatting
- [ ] New quirks seed file passes `TestSeedFiles` validations (UTF-8, heading, overview section, key takeaways)
- [ ] `outlook_new_win` resolves correctly in ontology registry
- [ ] Support matrix entries for `outlook_new_win` match `outlook_web` entries
- [ ] L3 skill files with deprecation headers still parse correctly via `parse_skill_meta()`

## Security Checklist

No new endpoints or routes in this plan. Changes are limited to:
- YAML data files (ontology definitions) — no user input path
- Markdown seed files (knowledge base content) — no user input path
- Python constants (CLIENT_MAP, SEED_MANIFEST) — no user input path
- Test files — no security surface

No auth, rate limiting, or input sanitization changes needed.

## Verification

- [ ] `make check` passes (includes lint, types, tests, frontend, security-check)
- [ ] `outlook_new_win` appears in `load_ontology().client_ids()`
- [ ] `outlook_new_win` has correct support matrix entries (matches `outlook_web`)
- [ ] New quirks seed passes all `TestSeedFiles` assertions
- [ ] Samsung foldable section includes Flex Mode, One UI versions, and code example
- [ ] L3 deprecation headers don't break `parse_skill_meta()` parsing
- [ ] Skill files with `priority: 3` are only loaded at >70% budget capacity (existing `should_load_skill` tests cover this)
