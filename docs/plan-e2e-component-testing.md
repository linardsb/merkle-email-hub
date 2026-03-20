# Plan: End-to-End Component Testing

**Status:** Pending
**Created:** 2026-03-19
**Prerequisite:** `docs/plan-component-extraction.md` (Done)

## Objective

Verify all 21 seeded components (email-shell + 10 original + 10 new) work end-to-end: backend API serves them correctly, frontend visual builder loads and renders them, property panels edit slots/tokens, preview assembles valid email HTML, and the Maizzle sidecar compiles the output.

---

## Stack Setup

### Services Required

| Service | Port | Start Command |
|---------|------|---------------|
| PostgreSQL | 5434 | `make db` |
| Redis | 6380 | `make db` |
| Backend (FastAPI) | 8891 | `make dev-be` |
| Frontend (Next.js) | 3000 | `make dev-fe` |
| Maizzle Sidecar | 3001 | `cd services/maizzle-builder && npm run dev` |

### First-Time Setup

```bash
# 1. Start database + Redis
make db

# 2. Run migrations
make db-migrate

# 3. Seed demo data (creates admin user + 21 components)
make seed-demo

# 4. Start all services (3 terminals)
make dev-be                                          # Terminal 1
make dev-fe                                          # Terminal 2
cd services/maizzle-builder && npm install && npm run dev   # Terminal 3
```

### Login Credentials

- **URL:** http://localhost:3000/login
- **Email:** `admin@email-hub.dev`
- **Password:** printed by `make seed-demo` output (check `AUTH__DEMO_USER_PASSWORD` in `.env`)

---

## Test Plan

### Phase 1: Backend API Verification

Verify the component API serves all 21 components with correct data.

#### Test 1.1 — List All Components

```bash
# Get a JWT token first
TOKEN=$(curl -s -X POST http://localhost:8891/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@email-hub.dev","password":"YOUR_PASSWORD"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List components
curl -s http://localhost:8891/api/v1/components/?page_size=25 \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** 21 components returned. Check for:
- [x] `email-shell` present with category `structure`
- [x] All 10 new slugs present: `column-layout-2`, `column-layout-3`, `column-layout-4`, `reverse-column`, `full-width-image`, `preheader`, `article-card`, `image-grid`, `logo-header`, `navigation-bar`
- [x] All 10 original slugs present

#### Test 1.2 — Component Versions Have Slots + Tokens

```bash
# Pick a component ID (e.g., article-card)
COMPONENT_ID=<id from Test 1.1>

curl -s http://localhost:8891/api/v1/components/$COMPONENT_ID/versions \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** Version 1 returned with:
- [x] `html_source` — non-empty HTML string
- [x] `slot_definitions` — array of `{slot_id, slot_type, selector, required}` objects (for components that have them)
- [x] `default_tokens` — JSON with `colors`, `fonts`, `font_sizes`, `spacing` keys (for components that have them)

**Components that MUST have slot_definitions:**
| Component | Slots |
|-----------|-------|
| email-shell | email_title, preheader, email_body |
| cta-button | cta_url, cta_text |
| hero-block | hero_image, headline, subtext, cta_url, cta_text |
| spacer | spacer_height |
| column-layout-2 | col_1, col_2 |
| column-layout-3 | col_1, col_2, col_3 |
| column-layout-4 | col_1, col_2, col_3, col_4 |
| reverse-column | primary_content, secondary_content |
| full-width-image | image_url, image_alt, link_url |
| preheader | preheader_text, view_online_url |
| article-card | image_url, image_alt, heading, body_text, cta_text, cta_url |
| image-grid | image_1, image_2, link_1, link_2 |
| logo-header | logo_url, logo_alt, logo_width |
| navigation-bar | nav_links |

#### Test 1.3 — Filter by Category

```bash
curl -s "http://localhost:8891/api/v1/components/?category=structure" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** Returns only structure components (email-shell, email-header, email-footer, spacer, divider, column-layout-2/3/4, reverse-column, preheader, logo-header, navigation-bar).

#### Test 1.4 — Search by Name

```bash
curl -s "http://localhost:8891/api/v1/components/?search=column" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** Returns column-layout-2, column-layout-3, column-layout-4, reverse-column.

---

### Phase 2: Frontend Visual Builder

#### Test 2.1 — Navigate to Workspace

1. Open http://localhost:3000/login
2. Login with admin credentials
3. Navigate to the "Summer Campaign 2026" project
4. Open the workspace (should be at `/projects/<id>/workspace`)

**Expected:** Workspace loads with code editor panel and visual builder panel.

#### Test 2.2 — Component Palette Loads

1. In the visual builder, look for the component palette (left sidebar)
2. Verify it shows component cards

**Expected:**
- [x] All 21 components visible (may need to scroll or paginate)
- [x] Category filter buttons work (structure, content, action, social, commerce)
- [x] Search box filters components by name
- [x] Each card shows component name and category badge

#### Test 2.3 — Drag & Drop Components onto Canvas

Test each of these components (one at a time):

1. **email-shell** — Drag onto empty canvas
   - Expected: Full HTML document shell appears in preview
2. **column-layout-2** — Drag onto canvas
   - Expected: Two-column layout visible, columns side-by-side
3. **article-card** — Drag onto canvas
   - Expected: Image left, text right layout
4. **hero-block** — Drag onto canvas
   - Expected: Background image with overlaid text
5. **cta-button** — Drag onto canvas
   - Expected: Centered button

**For each component verify:**
- [x] Drag cursor changes on grab
- [x] Drop zones highlight on hover
- [x] Component appears on canvas at correct position
- [x] Preview iframe updates with the component HTML
- [x] No console errors (open DevTools → Console)

#### Test 2.4 — Component Reordering

1. Add 3+ components to the canvas
2. Drag a component to reorder it (move it above/below another)

**Expected:**
- [x] Reorder animation smooth
- [x] Preview updates to reflect new order
- [x] Undo (Ctrl+Z) reverts the reorder

#### Test 2.5 — Delete Component from Canvas

1. Select a component on the canvas
2. Click the delete/remove button (trash icon or X)

**Expected:**
- [x] Component removed from canvas
- [x] Preview updates
- [x] Undo brings it back

---

### Phase 3: Property Panel — Slot Editing

#### Test 3.1 — Content Tab (Slot Fills)

1. Drag `article-card` onto canvas
2. Click it to select
3. Open the Content tab in the right property panel

**Expected:**
- [x] Slot editors appear for: image_url, image_alt, heading, body_text, cta_text, cta_url
- [x] Each slot has a label matching its `slot_id`
- [x] `slot_type` determines the editor control:
  - `image` → image URL input
  - `headline` → text input
  - `body` → textarea
  - `cta` → URL input or text input

4. Edit the `heading` slot — type "Summer Sale 2026"
5. Edit the `body_text` slot — type "Don't miss our biggest sale of the year."
6. Edit the `cta_text` slot — type "Shop Now"
7. Edit the `cta_url` slot — type "https://example.com/summer"

**Expected:**
- [x] Preview updates in real-time with new content
- [x] HTML in code editor reflects the slot fills

#### Test 3.2 — Column Layout Slots

1. Drag `column-layout-2` onto canvas
2. Select it, open Content tab

**Expected:**
- [x] Two slot editors: `col_1` and `col_2`
- [x] Editing either updates the respective column in preview

#### Test 3.3 — Preheader Slots

1. Drag `preheader` onto canvas
2. Select it, open Content tab

**Expected:**
- [x] Slot for `preheader_text` — editable
- [x] Slot for `view_online_url` — editable (marked optional)

---

### Phase 4: Property Panel — Style & Responsive

#### Test 4.1 — Style Tab (Token Overrides)

1. Select the `article-card` component
2. Open the Style tab

**Expected:**
- [x] Color pickers restricted to design system palette (blue, purple, amber from demo project)
- [x] Font selector shows available fonts
- [x] Changing a color updates the preview

3. Change the heading color to the project's primary color (#2563EB)
4. Change the CTA background color

**Expected:**
- [x] Preview reflects the color change
- [x] Code editor shows updated inline styles

#### Test 4.2 — Responsive Tab

1. Select a `column-layout-2` component
2. Open the Responsive tab

**Expected:**
- [x] Toggle for "Stack on mobile" (should default to enabled)
- [x] Mobile font size adjustment
- [x] Mobile padding adjustment

3. Toggle the preview between Desktop and Mobile widths using the toolbar

**Expected:**
- [x] Desktop: columns side by side
- [x] Mobile (narrow preview): columns stack vertically

#### Test 4.3 — Advanced Tab

1. Select any component
2. Open the Advanced tab

**Expected:**
- [x] Custom CSS class input
- [x] MSO conditional checkbox
- [x] Dark mode property overrides
- [x] HTML attributes editor
- [x] "View Source" button shows the raw component HTML

---

### Phase 5: Preview Assembly

#### Test 5.1 — Multi-Component Email Assembly

Build a complete email by dragging components in this order:

1. `preheader`
2. `logo-header`
3. `navigation-bar`
4. `hero-block`
5. `spacer`
6. `article-card`
7. `divider`
8. `column-layout-2`
9. `cta-button`
10. `spacer`
11. `email-footer`

**Expected:**
- [x] Preview shows a complete, realistic email layout
- [x] All sections render in the correct order
- [x] No broken HTML visible (unclosed tags, missing images, etc.)

#### Test 5.2 — Dark Mode Preview

1. With the multi-component email from 5.1, toggle dark mode preview (if available in toolbar)

**Expected:**
- [x] Background colors switch to dark (#1a1a2e)
- [x] Text colors switch to light (#e0e0e0)
- [x] Components with dark mode CSS classes respond correctly

#### Test 5.3 — Code Editor Sync

1. Switch to the code editor view
2. Verify the assembled HTML is present

**Expected:**
- [x] Full HTML document with all component sections
- [x] MSO conditional comments present
- [x] Dark mode `<style>` blocks present
- [x] `data-slot` attributes present on slotted elements

3. Edit a heading directly in the code editor

**Expected:**
- [x] Visual builder canvas updates to reflect the code change
- [x] No infinite sync loop (stable after 1-2 updates)

---

### Phase 6: Maizzle Build Integration

#### Test 6.1 — Sidecar Health Check

```bash
curl http://localhost:3001/health
```

**Expected:** `{"status":"ok","service":"maizzle-builder"}`

#### Test 6.2 — Preview Build via API

```bash
# Use the assembled HTML from Test 5.1 (or any component HTML)
curl -s -X POST http://localhost:3001/preview \
  -H "Content-Type: application/json" \
  -d '{"source":"<table role=\"presentation\" width=\"100%\"><tr><td>Hello</td></tr></table>"}' \
  | python -m json.tool
```

**Expected:**
- [x] Returns `{html: "...", build_time_ms: N}`
- [x] HTML has CSS inlined
- [x] HTML is prettified (not minified)

#### Test 6.3 — Production Build via API

```bash
curl -s -X POST http://localhost:3001/build \
  -H "Content-Type: application/json" \
  -d '{"source":"<table role=\"presentation\" width=\"100%\"><tr><td>Hello</td></tr></table>","production":true}' \
  | python -m json.tool
```

**Expected:**
- [x] Returns minified HTML
- [x] Comments stripped
- [x] CSS inlined

#### Test 6.4 — Build via Backend API

```bash
curl -s -X POST http://localhost:8891/api/v1/email/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"html":"<table role=\"presentation\" width=\"100%\"><tr><td style=\"padding:20px\">Test email</td></tr></table>"}' \
  | python -m json.tool
```

**Expected:**
- [x] Backend proxies to Maizzle sidecar
- [x] Returns compiled HTML

#### Test 6.5 — Build with Full Component HTML

1. Copy the full assembled HTML from the code editor (Test 5.3)
2. Send it to the build endpoint
3. Verify the output is valid, compilable email HTML

```bash
curl -s -X POST http://localhost:8891/api/v1/email/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"html":"PASTE_ASSEMBLED_HTML_HERE"}' \
  | python -m json.tool
```

**Expected:**
- [x] Compiled HTML returned
- [x] MSO conditionals preserved
- [x] VML elements preserved
- [x] CSS inlined into `style` attributes

---

### Phase 7: Section Adapter Verification

#### Test 7.1 — Programmatic Section Adapter Check

Run this script to verify all new components convert to SectionBlock:

```bash
uv run python -c "
from app.components.data.seeds import COMPONENT_SEEDS
from app.components.section_adapter import SectionAdapter, SlotHint

adapter = SectionAdapter()

for seed in COMPONENT_SEEDS:
    slug = seed['slug']
    slot_defs = seed.get('slot_definitions') or []
    hints = [SlotHint(s['slot_id'], s['selector']) for s in slot_defs]

    class FakeVersion:
        component_id = 0
        version_number = 1
        html_source = seed['html_source']
        default_tokens = seed.get('default_tokens')

    try:
        block = adapter.convert(FakeVersion(), hints)
        slot_count = len(block.slot_definitions)
        token_status = 'tokens' if block.default_tokens else 'no-tokens'
        mso = 'mso' if block.has_mso_wrapper else 'no-mso'
        print(f'OK  {slug:25s}  slots={slot_count}  {token_status:10s}  {mso}')
    except Exception as e:
        print(f'FAIL {slug}: {e}')
"
```

**Expected:** All 21 components print `OK` with correct slot counts.

---

### Phase 8: QA Check on Components

#### Test 8.1 — Run QA via API

For each new component, run the QA endpoint to compute compatibility:

```bash
COMPONENT_ID=<id of column-layout-2>

curl -s -X POST http://localhost:8891/api/v1/components/$COMPONENT_ID/versions/1/qa \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:**
- [x] QA checks execute without error
- [x] Compatibility result returned with per-client scores
- [x] Components targeting `_COMPAT_FULL` get "full" across all clients
- [x] `reverse-column` and `hero-block` may get "partial" for Samsung

#### Test 8.2 — Compatibility Badge

```bash
curl -s http://localhost:8891/api/v1/components/$COMPONENT_ID/compatibility \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected:** Returns `{"badge": "full", "details": {...}}` with per-client support levels.

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| No components in palette | Run `make seed-demo`, check backend logs for seed errors |
| 401 on API calls | Token expired — re-login, get fresh JWT |
| Preview blank | Check browser console for errors, verify component HTML isn't empty |
| Maizzle build fails | Check `http://localhost:3001/health`, ensure sidecar is running |
| Columns don't stack on mobile | Check that `@media (max-width: 599px)` CSS is present in component |
| Dark mode not working | Verify `@media (prefers-color-scheme: dark)` and `[data-ogsc]` selectors in component HTML |
| Slot edits don't show in preview | Check that `data-slot` attributes match `slot_definitions[].selector` |
| Code editor out of sync | Refresh page — sync engine should reconnect |

## Success Criteria

- [ ] All 21 components visible in palette
- [ ] Each component can be dragged onto canvas and renders correctly
- [ ] Slot editing updates preview in real-time for all components with slots
- [ ] Style/token overrides apply design system colors
- [ ] Responsive preview shows mobile stacking for column layouts
- [ ] Multi-component email assembles into valid HTML
- [ ] Maizzle sidecar compiles the assembled HTML without errors
- [ ] Section adapter converts all 21 components to SectionBlock
- [ ] QA checks pass on all components
