# Plan: Fix Design Sync — Empty Code Editor After Import

## Context
When a design import completes and the user clicks "Open in Workspace", the code editor is empty despite the preview showing the correct rendered email. This is a **frontend bug** in the workspace page's interaction with the Yjs collaborative editing layer.

### Root Cause
In `code-editor.tsx:206-209`, when `collaborative` is truthy, `value` and `onChange` are NOT passed to CodeMirror — Yjs is expected to manage the document content. The race condition:

1. `useCollaboration` sets `collabDoc` **synchronously** (line 39 of `use-collaboration.ts`)
2. `awareness` is set **asynchronously** after a dynamic `import("y-protocols/awareness")` resolves
3. When `latestVersion.html_source` loads, `setEditorContent()` runs → CodeMirror is still in controlled mode (awareness=null → `collaborative` is undefined) → HTML appears briefly
4. Then `awareness` resolves → `collaborative` becomes truthy → CodeMirror drops `value`/`onChange` → **editor goes empty**
5. The Yjs Y.Doc was created empty (`new Y.Doc()`) and nobody populates it with the loaded HTML

The preview still works because `triggerPreview` uses `latestVersion.html_source` directly (not `editorContent` state).

## Files to Modify
- `cms/apps/web/src/app/projects/[id]/workspace/page.tsx` — Populate Yjs doc when version loads

## Implementation Steps

### Step 1: Populate Yjs document when template version loads

In `workspace/page.tsx`, modify the `useEffect` at line 198 to also populate the Yjs Y.Text when `collabDoc` is available and the Y.Text is empty:

```typescript
// Sync editor content when version data loads
const demoCompiledRef = useRef(false);
useEffect(() => {
  if (latestVersion?.html_source) {
    setEditorContent(latestVersion.html_source);
    setSavedContent(latestVersion.html_source);
    setSaveStatus("idle");

    // Populate Yjs document so collaborative editor shows the content
    if (collabDoc) {
      const yText = collabDoc.getText("content");
      if (yText.length === 0) {
        yText.insert(0, latestVersion.html_source);
      }
    }

    // Auto-compile in demo mode so preview is always populated
    if (
      process.env.NEXT_PUBLIC_DEMO_MODE === "true" &&
      !demoCompiledRef.current
    ) {
      demoCompiledRef.current = true;
      const sanitized = sanitizeHtml(stripAnnotations(latestVersion.html_source));
      triggerPreview({ source_html: sanitized })
        .then((r) => {
          if (r) {
            setCompiledHtml(r.compiled_html);
            setBuildTimeMs(r.build_time_ms);
          }
        })
        .catch(() => {
          /* demo compile failed silently */
        });
    }
  }
}, [latestVersion?.html_source, triggerPreview, collabDoc]);
```

**Key details:**
- `collabDoc.getText("content")` matches the field name used in `use-collaboration.ts:40` (`ydoc.getText("content")`)
- The `yText.length === 0` guard prevents overwriting content that was already populated (e.g., from a real WebSocket sync in production mode)
- Adding `collabDoc` to the dependency array ensures this runs even if the doc is created after the version already loaded (covers the async awareness race)

### Step 2: Handle the reverse race (awareness loads BEFORE version)

If `collabDoc` is set before `latestVersion` arrives, the current useEffect handles it fine — the effect will re-run when `latestVersion.html_source` changes. No additional handling needed.

If `collabDoc` changes (e.g., template switch triggers new room), the existing cleanup in `useCollaboration` destroys the old doc and creates a new one. The `demoCompiledRef` should also be reset on template change:

In the workspace page, add a reset effect:

```typescript
// Reset demo compile flag when template changes
useEffect(() => {
  demoCompiledRef.current = false;
}, [activeTemplateId]);
```

This ensures auto-compile runs again when switching to a new design-imported template.

## Security Checklist
- [x] No new endpoints — frontend-only fix
- [x] No user input handling changes
- [x] No security implications

## Verification
- [ ] `make check-fe` passes (TypeScript + unit tests)
- [ ] Manual test: Import design → Open in Workspace → code editor shows HTML
- [ ] Manual test: Switch templates in workspace → editor updates correctly
- [ ] Manual test: Existing templates (non-imported) still work in code editor
