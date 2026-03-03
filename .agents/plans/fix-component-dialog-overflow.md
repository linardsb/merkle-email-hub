# Plan: Fix Component Detail Dialog Code Overflow

## Context
When clicking a component in the component library, the detail dialog opens showing HTML source code. The code stretches outside the dialog boundaries because:
1. Dialog width (`max-w-3xl` = 48rem) is too narrow for email HTML which has long lines
2. The `<pre>` block inside `ScrollArea` doesn't properly constrain horizontal overflow

## Files to Modify
- `cms/apps/web/src/components/components/component-detail-dialog.tsx` — widen dialog + fix overflow

## Implementation Steps

### Step 1: Widen dialog and constrain overflow

In `component-detail-dialog.tsx`, make these 3 changes:

**1a. Line 53** — Widen dialog from `max-w-3xl` to `max-w-5xl` (64rem):
```diff
- <DialogContent className="max-w-3xl">
+ <DialogContent className="max-w-5xl">
```

**1b. Lines 144 & 158** — Add `overflow-hidden` to `ScrollArea` wrappers so the `<pre>` can't escape:
```diff
- <ScrollArea className="mt-2 max-h-80">
+ <ScrollArea className="mt-2 max-h-80 overflow-hidden rounded-md">
```
```diff
- <ScrollArea className="mt-2 max-h-60">
+ <ScrollArea className="mt-2 max-h-60 overflow-hidden rounded-md">
```

**1c. Lines 145 & 159** — Move `rounded-md` from `<pre>` to `ScrollArea` (done above) and add `min-w-0` to prevent flex/grid expansion:
```diff
- <pre className="overflow-x-auto rounded-md bg-surface-muted p-4 text-xs text-foreground">
+ <pre className="min-w-0 overflow-x-auto bg-surface-muted p-4 text-xs text-foreground">
```
(Same change for both `<pre>` blocks)

That's it — 3 class changes across 5 lines.

## Verification
- [ ] `pnpm build` passes (from `cms/`)
- [ ] Dialog is wider and code fits within window bounds
- [ ] Long HTML lines scroll horizontally inside the code block (not the dialog)
- [ ] CSS source section also properly constrained
- [ ] Semantic Tailwind tokens only (no primitive colors)
