import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { BuilderSection } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";

// Mock DOMPurify
vi.mock("dompurify", () => ({
  default: { sanitize: (html: string) => html },
}));

// Mock ast-mapper
vi.mock("@/lib/builder-sync/ast-mapper", () => ({
  findContentRoot: vi.fn(),
}));

// Mock crypto.randomUUID for deterministic tests
const mockUUID = vi.fn(() => "mock-uuid-123");
vi.stubGlobal("crypto", { randomUUID: mockUUID });

import { useBuilderState } from "@/hooks/use-builder";

function makeSection(overrides: Partial<BuilderSection> = {}): BuilderSection {
  return {
    id: overrides.id ?? "sec-1",
    componentId: 1,
    componentName: "Hero Banner",
    componentSlug: "hero-banner",
    category: "hero",
    html: "<table><tr><td>Hello</td></tr></table>",
    css: null,
    slotFills: {},
    tokenOverrides: {},
    slotDefinitions: [],
    defaultTokens: null,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
    ...overrides,
  };
}

describe("useBuilderState", () => {
  beforeEach(() => {
    mockUUID.mockReturnValue("mock-uuid-123");
  });

  it("initial state has empty sections and no selection", () => {
    const { result } = renderHook(() => useBuilderState());
    expect(result.current.sections).toEqual([]);
    expect(result.current.selectedSectionId).toBeNull();
  });

  it("ADD_SECTION appends section to list", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    expect(result.current.sections).toHaveLength(1);
    expect(result.current.sections[0]!.id).toBe("s1");
  });

  it("ADD_SECTION at index inserts at position", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    act(() => result.current.addSection(makeSection({ id: "s3" }), 1));
    expect(result.current.sections.map((s) => s.id)).toEqual([
      "s1",
      "s3",
      "s2",
    ]);
  });

  it("REMOVE_SECTION removes by id", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    act(() => result.current.removeSection("s1"));
    expect(result.current.sections).toHaveLength(1);
    expect(result.current.sections[0]!.id).toBe("s2");
  });

  it("REMOVE_SECTION clears selection if removed section was selected", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.selectSection("s1"));
    expect(result.current.selectedSectionId).toBe("s1");
    act(() => result.current.removeSection("s1"));
    expect(result.current.selectedSectionId).toBeNull();
  });

  it("DUPLICATE_SECTION clones with new id", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() =>
      result.current.addSection(
        makeSection({ id: "s1", componentName: "Header" }),
      ),
    );
    act(() => result.current.duplicateSection("s1"));
    expect(result.current.sections).toHaveLength(2);
    expect(result.current.sections[1]!.id).toBe("mock-uuid-123");
    expect(result.current.sections[1]!.componentName).toBe("Header");
  });

  it("DUPLICATE_SECTION inserts after original", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    act(() => result.current.duplicateSection("s1"));
    expect(result.current.sections.map((s) => s.id)).toEqual([
      "s1",
      "mock-uuid-123",
      "s2",
    ]);
  });

  it("MOVE_SECTION reorders correctly", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    act(() => result.current.addSection(makeSection({ id: "s3" })));
    act(() => result.current.moveSection(0, 2));
    expect(result.current.sections.map((s) => s.id)).toEqual([
      "s2",
      "s3",
      "s1",
    ]);
  });

  it("UPDATE_SECTION merges partial updates", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() =>
      result.current.updateSection("s1", { componentName: "Updated" }),
    );
    expect(result.current.sections[0]!.componentName).toBe("Updated");
  });

  it("SELECT_SECTION sets selectedId", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.selectSection("s1"));
    expect(result.current.selectedSectionId).toBe("s1");
  });

  it("SELECT_SECTION with null clears selection", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.selectSection("s1"));
    act(() => result.current.selectSection(null));
    expect(result.current.selectedSectionId).toBeNull();
  });

  it("SET_SECTIONS replaces all sections", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "old" })));
    act(() =>
      result.current.setSections([
        makeSection({ id: "new1" }),
        makeSection({ id: "new2" }),
      ]),
    );
    expect(result.current.sections.map((s) => s.id)).toEqual([
      "new1",
      "new2",
    ]);
  });

  it("UNDO reverts last action", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    expect(result.current.sections).toHaveLength(1);
    act(() => result.current.undo());
    expect(result.current.sections).toHaveLength(0);
  });

  it("REDO re-applies undone action", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    expect(result.current.sections).toHaveLength(2);

    act(() => result.current.undo());
    // Undo reverts to pre-action snapshot of last action
    expect(result.current.canRedo).toBe(true);

    act(() => result.current.redo());
    // Redo moves historyIndex forward, canRedo becomes false
    expect(result.current.canRedo).toBe(false);
    expect(result.current.canUndo).toBe(true);
    // Redo restores the pre-action snapshot at the next index
    expect(result.current.historyIndex).toBe(2);
  });

  it("UNDO with no history is no-op", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.undo());
    expect(result.current.sections).toEqual([]);
  });

  it("REDO with no future is no-op", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.redo());
    expect(result.current.sections).toEqual([]);
  });

  it("canUndo and canRedo reflect state", () => {
    const { result } = renderHook(() => useBuilderState());
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);

    act(() => result.current.addSection(makeSection({ id: "s1" })));
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);

    act(() => result.current.undo());
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it("new action after undo clears redo stack", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.addSection(makeSection({ id: "s2" })));
    act(() => result.current.undo());
    expect(result.current.canRedo).toBe(true);

    act(() => result.current.addSection(makeSection({ id: "s3" })));
    expect(result.current.canRedo).toBe(false);
  });

  it("MOVE_SECTION with invalid fromIndex is no-op", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.moveSection(-1, 0));
    expect(result.current.sections).toHaveLength(1);
  });

  it("DUPLICATE_SECTION with nonexistent id is no-op", () => {
    const { result } = renderHook(() => useBuilderState());
    act(() => result.current.addSection(makeSection({ id: "s1" })));
    act(() => result.current.duplicateSection("nonexistent"));
    expect(result.current.sections).toHaveLength(1);
  });
});
