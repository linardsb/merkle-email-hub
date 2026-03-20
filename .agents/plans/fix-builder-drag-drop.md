# Plan: Fix Visual Builder Drag-and-Drop

## Context
Components from the palette cannot be dragged onto the canvas. The root cause: when the canvas is empty (`sections.length === 0`), `BuilderCanvas` renders a static placeholder div with no `useDroppable` hook — so `@dnd-kit` has no drop target to detect. The `DropZone` components only render when sections already exist.

## Files to Modify
- `cms/apps/web/src/components/builder/builder-canvas.tsx` — Add a droppable zone to the empty state

## Implementation Steps

### Step 1: Add droppable to the empty canvas state

In `builder-canvas.tsx`, the empty state (lines 43-54) is a plain div. Wrap it with `useDroppable` so palette items can be dropped onto it.

Replace the empty state block:

```tsx
if (sections.length === 0) {
  return (
    <EmptyDropZone />
  );
}
```

Add a new `EmptyDropZone` component (must be a separate component because hooks can't be conditional):

```tsx
function EmptyDropZone() {
  const { setNodeRef, isOver } = useDroppable({ id: "drop-zone-0" });

  return (
    <div ref={setNodeRef} className="flex h-full items-center justify-center">
      <div
        className={`flex flex-col items-center gap-3 rounded-lg border-2 border-dashed p-8 text-muted-foreground transition-colors ${
          isOver
            ? "border-interactive bg-interactive/10"
            : "border-border"
        }`}
      >
        <ArrowDown className="h-8 w-8 opacity-40" />
        <p className="text-sm">
          {"Drag components here to start building"}
        </p>
      </div>
    </div>
  );
}
```

This reuses the `"drop-zone-0"` ID that `handleExternalDrop` in `visual-builder-panel.tsx` already handles (line 212: `overId?.startsWith("drop-zone-")`), so no changes needed elsewhere.

## Security Checklist (scoped to this feature's files)
- [x] No `(x as any)` type casts
- [x] API calls use `authFetch` (no new API calls)
- [x] No `dangerouslySetInnerHTML` without DOMPurify
- [x] No token handling changes
- [x] No storage changes
- [x] No preview iframes

## Verification
- [ ] `make check-fe` passes (TypeScript + tests)
- [ ] Dragging a component from the palette onto the empty canvas adds it
- [ ] Visual feedback (border color change) appears when hovering over the empty drop zone
- [ ] After first component is added, subsequent drops between sections still work
- [ ] Reordering existing sections still works
