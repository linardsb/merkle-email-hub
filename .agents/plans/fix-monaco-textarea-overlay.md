# Plan: Fix Monaco Editor Textarea Overlay

## Context
The Monaco HTML editor in the workspace has a visible textarea overlaying the editor content (shown as a white rectangle with blue dashed border). This blocks user interaction — users cannot click into the editor, type, or paste HTML.

**Root cause:** Tailwind CSS v4's preflight sets `min-height` on `textarea:not([rows])` elements. Monaco editor uses an internal hidden `<textarea class="inputarea">` (without a `rows` attribute) for clipboard/IME input. Tailwind's rule forces this hidden textarea to have visible dimensions, making it overlay the editor content and intercept all input events.

## Files to Modify
- `cms/packages/ui/src/globals.css` — Add CSS override to neutralize Tailwind's interference with Monaco's internal textarea
- `cms/apps/web/src/components/workspace/editor/monaco-editor.tsx` — Add `accessibilitySupport: "off"` to prevent Monaco from making its textarea visible

## Implementation Steps

### Step 1: Add Monaco textarea CSS fix in globals.css
**File:** `cms/packages/ui/src/globals.css`

Add the following rule inside `@layer base` to ensure Tailwind's preflight doesn't affect Monaco's internal textarea:

```css
@layer base {
  /* existing rules... */

  /* Prevent Tailwind v4 preflight from resizing Monaco's hidden input textarea */
  .monaco-editor textarea {
    min-height: 0 !important;
    min-width: 0 !important;
  }
}
```

This targets `textarea` elements inside `.monaco-editor` and resets the min-height/min-width that Tailwind's preflight applies. Using `@layer base` keeps it in the proper cascade order.

### Step 2: Configure Monaco for robust textarea handling
**File:** `cms/apps/web/src/components/workspace/editor/monaco-editor.tsx`

Add `accessibilitySupport: "off"` to the editor options to prevent Monaco from making its textarea visible for accessibility reasons:

```tsx
options={{
  readOnly,
  fontSize: 13,
  // ... existing options ...
  accessibilitySupport: "off",  // Prevent textarea from becoming visible
}}
```

## Verification
- [ ] Open workspace page at `/en/projects/{id}/workspace`
- [ ] Verify no white rectangle/textarea overlay is visible in the editor
- [ ] Verify you can click into the editor and type
- [ ] Verify you can paste full HTML templates (Cmd+V / Ctrl+V)
- [ ] Verify syntax highlighting and line numbers work
- [ ] Verify editor toolbar (minimap toggle, word wrap) still works
- [ ] `pnpm build` passes (from `cms/`)
