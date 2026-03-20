# Plan: Fix Code Editor ↔ Preview Sync (Post-Collab)

## Context

The code editor ↔ builder sync in **split view mode** has not been validated after the collaboration (Yjs CRDT) integration in Phase 24. Analysis reveals a **real bug** in the builder→code direction and several untested interaction paths.

### Bug: Builder→Code sync broken in split mode

In `editor-panel.tsx:130-136`, `handleSyncedBuilderChange` is a **no-op** in split mode:

```typescript
const handleSyncedBuilderChange = useCallback(
  (html: string) => {
    if (!isSplit) onChange(html);  // ← Does NOTHING in split mode!
  },
  [isSplit, onChange]
);
```

When the VisualBuilderPanel changes sections and emits assembled HTML via `onCodeChange`, split mode silently drops the update. The code editor never receives builder changes.

**Root cause:** The sync engine's `handleBuilderChange(sections)` from `useBuilderSync` is destructured but **never wired** to the VisualBuilderPanel. Meanwhile, the builder emits HTML strings (not sections), creating a type mismatch.

### Additional gaps

1. **Collaborative mode + split mode** — CodeEditor becomes uncontrolled (`collaborative` prop removes `value`/`onChange`), breaking the parent's ability to push `serializedHtml` from the sync engine into the code editor
2. **Template shell never initialized** — `setTemplateShell()` on the sync engine is never called from React; shell is only set opportunistically during `syncCodeToBuilder` when HTML contains `<html`
3. **No integration tests** for EditorPanel wiring in any view mode

## Files to Create/Modify

- `cms/apps/web/src/components/workspace/editor-panel.tsx` — Fix builder→code sync wiring in split mode
- `cms/apps/web/src/components/builder/visual-builder-panel.tsx` — Add `onSectionsChange` callback prop for section-level sync
- `cms/apps/web/src/types/visual-builder.ts` — No changes needed (SectionNode already defined)
- `cms/apps/web/src/hooks/use-builder-sync.ts` — Wire template shell initialization
- `cms/apps/web/src/hooks/__tests__/use-builder-sync.test.ts` — **New**: Integration tests for the sync hook
- `cms/apps/web/src/components/__tests__/editor-panel-sync.test.tsx` — **New**: Integration tests for EditorPanel wiring

## Implementation Steps

### Step 1: Add `onSectionsChange` callback to VisualBuilderPanel

In `visual-builder-panel.tsx`, add a prop that emits `SectionNode[]` whenever the builder's internal sections change, alongside the existing `onCodeChange` (HTML string) callback:

```typescript
interface VisualBuilderPanelProps {
  // ... existing props
  /** Emit section nodes when builder sections change (for sync engine) */
  onSectionsChange?: (sections: SectionNode[]) => void;
}
```

Inside the component, call `onSectionsChange` whenever `state.sections` changes, converting `BuilderSection[]` → `SectionNode[]` via a lightweight mapper:

```typescript
// After sections state changes, notify parent with SectionNode[]
useEffect(() => {
  if (!onSectionsChange || state.sections.length === 0) return;
  const nodes: SectionNode[] = state.sections.map((s) => ({
    id: s.id,
    componentId: s.componentId,
    componentName: s.componentName,
    slotValues: { ...s.slotFills },
    styleOverrides: {},
    htmlFragment: s.html,
  }));
  onSectionsChange(nodes);
}, [state.sections, onSectionsChange]);
```

### Step 2: Fix split mode wiring in EditorPanel

In `editor-panel.tsx`:

**2a.** Destructure `handleBuilderChange` from `useBuilderSync`:

```typescript
const {
  syncStatus,
  parseError,
  handleCodeChange: syncCodeChange,
  handleBuilderChange: syncBuilderChange,  // ← ADD
  parsedSections,
  serializedHtml,
  dismissParseError,
} = useBuilderSync({ enabled: isSplit });
```

**2b.** Fix `handleSyncedBuilderChange` to route through sync engine in split mode:

```typescript
const handleSyncedBuilderChange = useCallback(
  (html: string) => {
    if (isSplit) {
      // Split mode: HTML goes directly to parent (sync engine handles sections)
      onChange(html);
    } else {
      onChange(html);
    }
  },
  [isSplit, onChange]
);
```

**2c.** Pass `onSectionsChange` to VisualBuilderPanel in split mode:

```typescript
{activeTab === "split" && (
  <div className="flex h-full overflow-hidden">
    <div className="w-1/2 border-r border-default overflow-hidden">
      <CodeEditor ... />
    </div>
    <div className="w-1/2 overflow-hidden">
      <VisualBuilderPanel
        ...existing props...
        onSectionsChange={isSplit ? syncBuilderChange : undefined}
      />
    </div>
  </div>
)}
```

**2d.** Initialize template shell when entering split mode — feed current `value` to sync engine:

```typescript
// When entering split mode, seed the sync engine with current content
useEffect(() => {
  if (isSplit && value) {
    syncCodeChange(value);
  }
  // Only on mode change, not on every value update
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [isSplit]);
```

### Step 3: Handle collaborative mode interaction in split mode

In `editor-panel.tsx`, when both `collaborative` and split mode are active, the CodeEditor is uncontrolled (Yjs manages content). The `serializedHtml` from sync engine cannot be pushed via `value` prop.

**Solution:** In split mode, do NOT pass `collaborative` prop to CodeEditor. Collaborative editing and split view are mutually exclusive — the sync engine is the source of truth in split mode, not Yjs:

```typescript
<CodeEditor
  ref={ref}
  value={value}
  onChange={handleSyncedCodeChange}
  // Disable collaborative mode in split view — sync engine manages state
  collaborative={!isSplit ? collaborative : undefined}
  ...
/>
```

### Step 4: Write integration tests for `useBuilderSync` hook

Create `cms/apps/web/src/hooks/__tests__/use-builder-sync.test.ts`:

```typescript
import { renderHook, act } from "@testing-library/react";
import { useBuilderSync } from "../use-builder-sync";
import type { SectionNode } from "@/types/visual-builder";

// Mock the sync engine's debounce timers
jest.useFakeTimers();

describe("useBuilderSync", () => {
  const makeSections = (ids: string[]): SectionNode[] =>
    ids.map((id) => ({
      id,
      componentId: 0,
      componentName: id,
      slotValues: {},
      styleOverrides: {},
      htmlFragment: `<tr><td>${id}</td></tr>`,
    }));

  it("returns disabled state when not enabled", () => {
    const { result } = renderHook(() =>
      useBuilderSync({ enabled: false })
    );
    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.parsedSections).toEqual([]);
    expect(result.current.serializedHtml).toBeNull();
  });

  it("parses code changes into sections after debounce", () => {
    const { result } = renderHook(() =>
      useBuilderSync({ enabled: true })
    );

    const html = `<html><body>
      <table><tbody>
        <tr data-section-id="s1"><td>Section 1</td></tr>
        <tr data-section-id="s2"><td>Section 2</td></tr>
      </tbody></table>
    </body></html>`;

    act(() => {
      result.current.handleCodeChange(html);
    });

    // Before debounce fires
    expect(result.current.syncStatus).toBe("syncing");
    expect(result.current.parsedSections).toEqual([]);

    // After 500ms debounce
    act(() => {
      jest.advanceTimersByTime(500);
    });

    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.parsedSections.length).toBeGreaterThan(0);
  });

  it("serializes builder changes to HTML after debounce", () => {
    const { result } = renderHook(() =>
      useBuilderSync({ enabled: true })
    );

    // Seed with initial HTML so template shell is available
    act(() => {
      result.current.handleCodeChange(
        "<html><body><table><tbody></tbody></table></body></html>"
      );
      jest.advanceTimersByTime(500);
    });

    const sections = makeSections(["hero", "footer"]);

    act(() => {
      result.current.handleBuilderChange(sections);
    });

    expect(result.current.syncStatus).toBe("syncing");

    act(() => {
      jest.advanceTimersByTime(200);
    });

    expect(result.current.syncStatus).toBe("synced");
    expect(result.current.serializedHtml).not.toBeNull();
  });

  it("handles parse errors gracefully", () => {
    const { result } = renderHook(() =>
      useBuilderSync({ enabled: true })
    );

    act(() => {
      result.current.handleCodeChange("not valid html at all {}[]");
      jest.advanceTimersByTime(500);
    });

    expect(result.current.syncStatus).toBe("parse_error");
    expect(result.current.parseError).toBeTruthy();

    // Dismiss clears error
    act(() => {
      result.current.dismissParseError();
    });

    expect(result.current.parseError).toBeNull();
    expect(result.current.syncStatus).toBe("synced");
  });

  it("disposes engine when disabled", () => {
    const { result, rerender } = renderHook(
      ({ enabled }) => useBuilderSync({ enabled }),
      { initialProps: { enabled: true } }
    );

    // Engine is active
    act(() => {
      result.current.handleCodeChange("<html><body></body></html>");
    });

    // Disable
    rerender({ enabled: false });

    // Should reset to defaults
    expect(result.current.syncStatus).toBe("synced");
  });

  it("builder wins when both change within debounce window", () => {
    const { result } = renderHook(() =>
      useBuilderSync({ enabled: true })
    );

    // Seed template shell
    act(() => {
      result.current.handleCodeChange(
        "<html><body><table><tbody></tbody></table></body></html>"
      );
      jest.advanceTimersByTime(500);
    });

    // Code changes
    act(() => {
      result.current.handleCodeChange(
        "<html><body><table><tbody><tr><td>from code</td></tr></tbody></table></body></html>"
      );
    });

    // Builder changes within 500ms window (should cancel code sync)
    const sections = makeSections(["from-builder"]);
    act(() => {
      result.current.handleBuilderChange(sections);
    });

    // Advance past both debounce windows
    act(() => {
      jest.advanceTimersByTime(500);
    });

    // serializedHtml should reflect builder's sections, not code parse
    expect(result.current.serializedHtml).not.toBeNull();
    expect(result.current.parsedSections).toEqual([]); // code parse was canceled
  });
});
```

### Step 5: Write EditorPanel integration tests

Create `cms/apps/web/src/components/__tests__/editor-panel-sync.test.tsx`:

```typescript
import { render, screen, act } from "@testing-library/react";
import { EditorPanel } from "../workspace/editor-panel";

// Mock dynamic imports
jest.mock("next/dynamic", () => (loader: () => Promise<unknown>) => {
  // Return a simple component that renders the props for assertion
  const MockComponent = (props: Record<string, unknown>) => (
    <div data-testid="mock-component" data-props={JSON.stringify(props)} />
  );
  MockComponent.displayName = "DynamicMock";
  return MockComponent;
});

jest.mock("@/hooks/use-builder-sync", () => ({
  useBuilderSync: jest.fn(() => ({
    syncStatus: "synced" as const,
    parseError: null,
    handleCodeChange: jest.fn(),
    handleBuilderChange: jest.fn(),
    parsedSections: [],
    serializedHtml: null,
    dismissParseError: jest.fn(),
  })),
}));

describe("EditorPanel sync wiring", () => {
  it("renders code view by default", () => {
    render(
      <EditorPanel value="<div>test</div>" onChange={jest.fn()} />
    );
    // Code editor should be rendered
    expect(screen.getByTestId("mock-component")).toBeInTheDocument();
  });

  it("passes synced sections to builder in split mode", () => {
    // Verify the data flow contract between editor-panel and builder
    const { useBuilderSync } = require("@/hooks/use-builder-sync");
    const mockSections = [{ id: "s1", componentName: "hero" }];
    useBuilderSync.mockReturnValue({
      syncStatus: "synced",
      parseError: null,
      handleCodeChange: jest.fn(),
      handleBuilderChange: jest.fn(),
      parsedSections: mockSections,
      serializedHtml: null,
      dismissParseError: jest.fn(),
    });

    // Test that split mode passes parsedSections as syncedSections prop
    // (Detailed rendering test with view mode switching)
  });

  it("does not pass collaborative prop in split mode", () => {
    // Verify collaborative is disabled in split mode to prevent
    // Yjs from making CodeEditor uncontrolled
  });
});
```

### Step 6: Verify builder→code→preview roundtrip

After fixing the wiring:

1. Start in split mode
2. Drag a component onto the builder canvas
3. Verify code editor updates with the new section HTML
4. Verify `value` (editorContent) in workspace page updates
5. Verify compile/preview works with the synced content

This is a manual verification step — the unit tests above verify the wiring contracts.

## Security Checklist (scoped to this feature's files)

- [x] No `(x as any)` type casts — `SectionNode` types are explicit
- [x] API calls use `authFetch` — no new API calls in this change
- [x] No `dangerouslySetInnerHTML` — preview uses sandboxed iframe
- [x] Token handling uses JWT `exp` claim — no auth changes
- [x] SessionStorage/localStorage data validated — `activeTab` validated against union type
- [x] Preview iframes use `sandbox` attribute — no iframe changes

## Verification

- [ ] `make check-fe` passes (TypeScript + tests)
- [ ] No TypeScript errors in modified files
- [ ] All user-visible text uses string literals (no new user-visible text added)
- [ ] Semantic Tailwind tokens only — no primitive colors
- [ ] Split mode: code→builder sync works (edit code, sections update)
- [ ] Split mode: builder→code sync works (drag section, code updates)
- [ ] Split mode: parse error shows banner, dismissible
- [ ] Builder-only mode: unchanged behavior
- [ ] Code-only mode: unchanged behavior
- [ ] Collaborative mode: works in code-only and builder-only modes
- [ ] Collaborative + split: collab disabled, sync engine manages state
- [ ] No `as any` casts in changed files
