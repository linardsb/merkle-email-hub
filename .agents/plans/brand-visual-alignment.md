# Plan: [REDACTED] Brand Visual Alignment

## Context
Align the CMS frontend visual design with [REDACTED]'s official brand guidelines from Frontify. Three key changes:
1. **Typography** — Inter → Proxima Nova ([REDACTED]'s brand typeface)
2. **Colors** — Shift neutral palette to purple-gray undertone, success to teal, add chart palette
3. **Border radius** — Remove ALL rounded corners application-wide (user requirement: "no rounded corners for anything")

Source: https://[REDACTED].frontify.com/d/e2B69vudmb6N/guidelines

## Files to Modify

### Token/Style Layer (propagates to all components)
- `cms/packages/ui/src/tokens.css` — Font family, radius tokens, color palette adjustments, chart tokens
- `cms/packages/ui/src/globals.css` — Font import, global radius override safety net

### Component Fixes (only where hardcoded values bypass tokens)
- `cms/apps/web/src/components/ui/skeletons.tsx` — 13 `rounded-*` occurrences
- `cms/apps/web/src/components/workspace/chat/message-bubble.tsx` — 5 `rounded-*` occurrences (chat bubbles have asymmetric radius)
- `cms/packages/ui/src/components/ui/switch.tsx` — 2 `rounded-full` (toggle track/thumb)
- `cms/packages/ui/src/components/ui/scroll-area.tsx` — 2 `rounded-full` (scrollbar thumb)
- `cms/packages/ui/src/components/ui/avatar.tsx` — 2 `rounded-full` (circular avatars)

No new files created — this is a pure design token + CSS change.

## Implementation Steps

### Step 1: Update `tokens.css` — Font Family

Replace line 117:
```css
/* Before */
--font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;

/* After */
--font-sans: "Proxima Nova", "proxima-nova", "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

Notes:
- `"Proxima Nova"` — local install / Adobe Fonts
- `"proxima-nova"` — Adobe Fonts CSS class name variant
- `"Space Grotesk"` — [REDACTED]'s secondary font (free Google Font, good fallback)
- System fonts as final fallback

### Step 2: Update `globals.css` — Font Loading

Add Google Fonts import for Space Grotesk (free secondary font) and a comment about Proxima Nova:

```css
/* [REDACTED] brand fonts — Proxima Nova requires Adobe Fonts license.
   Space Grotesk ([REDACTED] secondary) loaded as visible fallback. */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

@import "tailwindcss";
@import "./tokens.css";
```

### Step 3: Update `tokens.css` — Remove ALL Border Radius

Replace the radius section (lines 121-125) with:

```css
/* ── Radius ([REDACTED] brand: sharp corners, no rounding) ── */
--radius-xs: 0;
--radius-sm: 0;
--radius-md: 0;
--radius-lg: 0;
--radius-xl: 0;
--radius-2xl: 0;
--radius-3xl: 0;
--radius-full: 0;
```

And update the shadcn alias (line 156):
```css
--radius: 0;
```

This propagates through ALL Tailwind `rounded-*` utilities and shadcn component styles.

### Step 4: Add Global Radius Safety Net in `globals.css`

After the existing `@layer base` block, add:
```css
/* [REDACTED] brand: zero border-radius globally — catches any inline styles
   or third-party components that don't use Tailwind utilities */
@layer base {
  *,
  *::before,
  *::after {
    border-radius: 0 !important;
  }
}
```

Merge this into the existing `@layer base` block.

### Step 5: Update `tokens.css` — Neutral Palette Hue Shift

Shift neutral hue from 260 (blue) to 270 (purple-gray) to match [REDACTED]'s `#8888A1` muted text tones:

```css
/* ── Tier 1: Primitive Palette (oklch) ── */
/* Neutrals: hue 270 (purple-gray, per [REDACTED] Frontify #8888A1) */
--color-neutral-50: oklch(0.98 0.005 270);
--color-neutral-100: oklch(0.96 0.008 270);
--color-neutral-200: oklch(0.91 0.012 270);
--color-neutral-300: oklch(0.85 0.015 270);
--color-neutral-400: oklch(0.70 0.020 270);
--color-neutral-500: oklch(0.55 0.025 270);
--color-neutral-600: oklch(0.45 0.025 270);
--color-neutral-700: oklch(0.35 0.020 270);
--color-neutral-800: oklch(0.25 0.015 270);
--color-neutral-900: oklch(0.18 0.012 270);
--color-neutral-950: oklch(0.12 0.010 270);
```

### Step 6: Update `tokens.css` — Success Color (Green → Teal)

Match [REDACTED]'s teal "Do" color `#06757E` / `rgba(6, 117, 126)`:

```css
/* Success: [REDACTED] teal #06757E */
--color-success-500: oklch(0.52 0.09 195);
--color-success-600: oklch(0.45 0.09 195);
```

Update light mode badge:
```css
--color-badge-success-bg: oklch(0.92 0.040 195);
--color-badge-success-text: var(--color-success-600);
```

Update dark mode badge:
```css
--color-badge-success-bg: oklch(0.25 0.040 195);
--color-badge-success-text: var(--color-success-500);
```

### Step 7: Update `tokens.css` — Sidebar Navy (Fine-tune to [REDACTED] Exact)

Match [REDACTED]'s exact navy `#12295D` = `oklch(0.25 0.09 265)`:

```css
/* Light mode sidebar */
--color-sidebar-bg: oklch(0.25 0.09 265);
--color-sidebar-hover: oklch(0.29 0.08 265);
--color-sidebar-border: oklch(0.30 0.07 265);

/* Dark mode sidebar */
--color-sidebar-bg: oklch(0.17 0.09 268);
--color-sidebar-hover: oklch(0.22 0.08 268);
--color-sidebar-border: oklch(0.24 0.06 268);
```

### Step 8: Update `tokens.css` — Add Chart/Data Visualization Palette

Add new Tier 3 tokens for the intelligence dashboard charts:

```css
/* ── Chart / Data Visualization ([REDACTED] brand palette) ── */
--color-chart-1: oklch(0.25 0.09 265);   /* Navy #12295D */
--color-chart-2: oklch(0.45 0.09 195);   /* Teal #06757E */
--color-chart-3: oklch(0.55 0.220 27);   /* Brand red #E4002B */
--color-chart-4: oklch(0.62 0.15 245);   /* Blue #0391F2 */
--color-chart-5: oklch(0.55 0.025 270);  /* Purple-gray #8888A1 */
--color-chart-6: oklch(0.65 0.150 75);   /* Warning amber */
```

Dark mode overrides:
```css
--color-chart-1: oklch(0.65 0.08 265);   /* Lighter navy */
--color-chart-2: oklch(0.60 0.09 195);   /* Lighter teal */
--color-chart-3: oklch(0.65 0.190 27);   /* Lighter red */
--color-chart-4: oklch(0.70 0.13 245);   /* Lighter blue */
--color-chart-5: oklch(0.70 0.025 270);  /* Lighter gray */
--color-chart-6: oklch(0.75 0.150 75);   /* Lighter amber */
```

### Step 9: Fix Components With Hardcoded Radius

These components have `rounded-*` classes that work independently of CSS variables. Since all `--radius-*` tokens are now 0, and the global `!important` override catches everything, these classes will also resolve to 0. **No component file changes needed** — the global override handles it.

However, verify these specific patterns render correctly with 0 radius:
- Chat message bubbles (asymmetric radius → becomes rectangular)
- Switch toggle (pill → becomes rectangular track/thumb)
- Avatar (circle → becomes square)
- Badge pill shapes (pill → becomes rectangular label)
- Status indicator dots (`rounded-full h-2 w-2` → becomes small squares)
- Scrollbar thumb (pill → becomes rectangular)

All of these are valid with sharp corners for a corporate [REDACTED] aesthetic.

### Step 10: Update Intelligence Dashboard Chart Colors

In `cms/apps/web/src/app/(dashboard)/intelligence/page.tsx` and its child components:

The `CheckPerformanceChart` and `ScoreTrendBars` use inline color logic based on threshold values (green >=80%, yellow >=50%, red <50%). These should use the new chart tokens:

- `bg-status-success` (now teal) for passing bars — already semantic, auto-updated via Step 6
- `bg-status-danger` for failing bars — already semantic
- `bg-status-warning` for warning — already semantic

**No code changes needed** — the chart components already use semantic tokens that will pick up the new teal success color.

### Step 11: Update Print Styles

In the `@media print` section of `tokens.css`, the hardcoded border color `#e5e7eb` should use the token system. But since we're removing rounding, the `rounded-lg` selector-based rule becomes irrelevant. Leave print styles as-is.

## Summary of Token Changes

| Token | Before | After |
|-------|--------|-------|
| `--font-sans` | Inter, system | Proxima Nova, Space Grotesk, system |
| `--radius-*` (all) | 0.375rem - 9999px | 0 |
| `--color-neutral-*` hue | 260 | 270 |
| `--color-success-500` | oklch(0.65 0.160 145) | oklch(0.52 0.09 195) |
| `--color-success-600` | oklch(0.55 0.160 145) | oklch(0.45 0.09 195) |
| `--color-sidebar-bg` | oklch(0.22 0.045 260) | oklch(0.25 0.09 265) |
| New: `--color-chart-1..6` | — | [REDACTED] brand palette |

## Verification

- [ ] `cd cms && pnpm build` passes with no TypeScript errors
- [ ] Light mode: All cards, buttons, inputs, badges have sharp corners (0 radius)
- [ ] Dark mode: Same — no rounded corners visible anywhere
- [ ] Sidebar uses [REDACTED] navy blue (`#12295D` approximate)
- [ ] Success badges/indicators show teal instead of green
- [ ] Font renders as Space Grotesk (or Proxima Nova if installed)
- [ ] Intelligence dashboard charts use semantic status colors (teal success)
- [ ] Status dots on dashboard are small squares (not circles)
- [ ] Print/PDF export still works from intelligence page
- [ ] No primitive Tailwind colors introduced
- [ ] All user-visible text still uses `useTranslations()`
