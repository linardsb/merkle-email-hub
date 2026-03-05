# Plan: Fix Dark Mode Text Readability

## Context

Text across the workspace and settings pages is unreadable in dark mode due to two issues:

1. **Wrong token**: `text-muted` is used in ~30 places but resolves to `--color-muted` → `--color-surface-muted` (a *background* color: `neutral-100` light / `neutral-800` dark). This makes text nearly invisible in both modes.
2. **Weak contrast**: `--color-foreground-muted` in dark mode is `neutral-400` (oklch 0.70) which gives only ~3.5:1 contrast against `neutral-900`/`neutral-950` backgrounds — below WCAG AA 4.5:1 minimum.

## Root Cause

- `text-muted` in Tailwind v4 → `color: var(--color-muted)` → `var(--color-surface-muted)` — this is a **surface/background** color, not a text color
- The correct class is `text-muted-foreground` → `color: var(--color-muted-foreground)` → `var(--color-foreground-muted)`

## Files to Modify

### Token fix (1 file)
- `cms/packages/ui/src/tokens.css` — Bump dark mode `--color-foreground-muted` from `neutral-400` to `neutral-300`

### Component fixes — replace `text-muted` with `text-muted-foreground` (10 files)
- `cms/apps/web/src/app/(dashboard)/settings/page.tsx` — 4 instances
- `cms/apps/web/src/app/(dashboard)/settings/translations/page.tsx` — 1 instance
- `cms/apps/web/src/components/settings/translation-table.tsx` — 7 instances (text-muted for text color; keep `placeholder:text-muted` as-is since placeholder color is separate)
- `cms/apps/web/src/components/workspace/editor-panel.tsx` — 2 instances
- `cms/apps/web/src/components/workspace/liquid-builder/block-if.tsx` — 3 instances
- `cms/apps/web/src/components/workspace/liquid-builder/block-canvas.tsx` — 1 instance
- `cms/apps/web/src/components/workspace/liquid-builder/block-assign.tsx` — 1 instance
- `cms/apps/web/src/components/workspace/liquid-builder/block-for.tsx` — 3 instances
- `cms/apps/web/src/components/workspace/liquid-builder/block-output.tsx` — 2 instances
- `cms/apps/web/src/components/workspace/collaboration/connection-status.tsx` — 1 instance
- `cms/apps/web/src/components/workspace/liquid-builder/liquid-preview.tsx` — 1 instance
- `cms/apps/web/src/components/workspace/liquid-builder/block-node.tsx` — 3 instances
- `cms/apps/web/src/components/workspace/liquid-builder/block-palette.tsx` — 1 instance

**Note**: `placeholder:text-muted` in `block-raw.tsx` and `translation-table.tsx` should stay — `--color-muted` is acceptable for placeholder styling since `--color-input-placeholder` is already separately defined, but `placeholder:text-muted` resolves to the same muted surface color. Change these to `placeholder:text-muted-foreground` for consistency.

## Implementation Steps

### Step 1: Fix dark mode token contrast

In `cms/packages/ui/src/tokens.css`, line 188:

```css
/* Before */
--color-foreground-muted: var(--color-neutral-400);

/* After */
--color-foreground-muted: var(--color-neutral-300);
```

This changes oklch from 0.70 → 0.85, giving ~6:1 contrast against `neutral-900` and ~7.5:1 against `neutral-950`. Both pass WCAG AA.

### Step 2: Fix `text-muted` → `text-muted-foreground` across all component files

For each file listed above, replace all instances of `text-muted` (when used as text color, not as `placeholder:text-muted` or `bg-muted`) with `text-muted-foreground`.

Regex pattern: replace ` text-muted(?!-)` with ` text-muted-foreground` — but verify each file manually to avoid breaking `placeholder:text-muted` or `bg-muted` classes.

Also fix `placeholder:text-muted` → `placeholder:text-muted-foreground` in:
- `cms/apps/web/src/components/workspace/liquid-builder/block-raw.tsx`
- `cms/apps/web/src/components/settings/translation-table.tsx`

### Step 3: Verify no remaining `text-muted` misuse

Run: `grep -rn 'text-muted[^-]' cms/apps/web/src/` to confirm zero results.

## Verification

- [ ] `pnpm build` passes (from `cms/`)
- [ ] No TypeScript errors
- [ ] `grep -rn 'text-muted[^-]' cms/apps/web/src/` returns zero results (or only `placeholder:` prefixed)
- [ ] Dark mode: settings page text is clearly readable
- [ ] Dark mode: workspace toolbar buttons/labels are clearly readable
- [ ] Light mode: no regressions (text still readable)
- [ ] Semantic Tailwind tokens only (no primitive colors)
