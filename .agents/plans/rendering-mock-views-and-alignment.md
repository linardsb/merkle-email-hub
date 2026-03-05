# Plan: Rendering Mock Views + Table Column Alignment Fix

## Context
The Renderings page has two issues:
1. **Broken tile images**: `screenshot_url` uses `picsum.photos` external URLs which show broken image icons. Need inline SVG data URIs that look like email rendering screenshots (similar to how briefs use inline SVG thumbnails).
2. **Column misalignment**: The Recent Tests table header (`<th>` elements) doesn't align with the row data (a `<button>` inside a single `colSpan={7}` `<td>` using flex spans with hardcoded widths). The Template, Provider, Compatibility columns are visibly misaligned.

## Files to Modify

1. `cms/apps/web/src/lib/demo/data/renderings.ts` — Replace `picsum.photos` URLs with inline SVG data URIs
2. `cms/apps/web/src/components/renderings/rendering-test-list.tsx` — Fix column alignment between header and rows

## Implementation Steps

### Step 1: Create inline SVG email mockup generator in `renderings.ts`

Add a `generateEmailMockupSvg(clientId, testId, status)` function that returns a `data:image/svg+xml,...` URI. The SVG should look like a simplified email screenshot:

- 600x400 viewport
- Background: light gray (#f4f4f4) for light-mode clients, dark (#1a1a2e) for dark-mode clients
- Email body white card centered
- Header bar with colored logo placeholder rectangle
- Hero image area (colored rectangle)
- 3-4 lines of "text" (gray bars)
- CTA button (colored rectangle)
- Footer area (thin gray bars)
- Subtle per-client variations:
  - **Outlook desktop** (outlook_2016, outlook_2019, outlook_365, windows_mail): Slightly broken layout — hero shifted, wider gaps (simulating Word rendering engine issues)
  - **Gmail** (gmail_web, gmail_workspace): Clean but with a "clipped" indicator line near the bottom
  - **Apple/iOS**: Clean, pixel-perfect rendering
  - **Dark mode** (ios_dark_mode): Dark background, inverted colors
  - **Thunderbird/Yahoo/AOL**: Minor spacing differences
- Use `encodeURIComponent` to make it URL-safe as data URI
- Color the hero section with a seeded hue so each client-test combo looks distinct

Replace the `screenshot_url` line in `generateResult()`:
```ts
// Before:
screenshot_url: `https://picsum.photos/seed/${clientId}-${testId}/600/400`,

// After:
screenshot_url: generateEmailMockupSvg(clientId, testId, resultStatusFromIssues(issues)),
```

Also replace comparison URLs:
```ts
// Before:
baseline_url: `https://picsum.photos/seed/${cid}-3/600/400`,
current_url: `https://picsum.photos/seed/${cid}-1/600/400`,

// After:
baseline_url: generateEmailMockupSvg(cid, 3, "pass"),
current_url: generateEmailMockupSvg(cid, 1, "pass"),
```

### Step 2: Fix table column alignment in `rendering-test-list.tsx`

The root issue: header uses `<th>` elements in a table row, but data rows use a `<button>` with flex layout inside a single `<td colSpan={7}>`. The flex widths don't match the table column widths.

**Fix approach**: Convert the table to a CSS grid-based layout so both header and rows use the same column template. This eliminates the table/flex mismatch.

Replace the `<table>` structure with:
```tsx
{/* Header row */}
<div className="grid grid-cols-[2rem_6rem_1fr_7rem_5rem_3.5rem_8rem] items-center border-b border-card-border pb-2 text-sm">
  <div /> {/* chevron */}
  <div className="font-medium text-foreground-muted">{t("status")}</div>
  <div className="font-medium text-foreground-muted">{t("template")}</div>
  <div className="font-medium text-foreground-muted">{t("provider")}</div>
  <div className="font-medium text-foreground-muted">{t("compatibility")}</div>
  <div className="font-medium text-foreground-muted">{t("clients")}</div>
  <div className="font-medium text-foreground-muted">{t("date")}</div>
</div>

{/* Data rows — each row button uses the same grid */}
<button className="grid w-full grid-cols-[2rem_6rem_1fr_7rem_5rem_3.5rem_8rem] items-center ...">
  {/* same column slots */}
</button>
```

This ensures perfect alignment because both header and rows share the exact same `grid-cols` template.

## Verification
- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] All user-visible text uses `useTranslations()`
- [ ] Semantic Tailwind tokens only (no primitive colors)
- [ ] Tiles show colored email mockup SVGs instead of broken images
- [ ] Table columns (Status, Template, Provider, Compatibility, Clients, Date) align between header and rows
- [ ] Screenshot dialog still works when clicking a tile
- [ ] Screenshot dialog shows the SVG mockup properly
