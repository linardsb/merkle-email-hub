import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useEditorState } from "../use-editor-state";

describe("useEditorState", () => {
  it("seeds editorContent and savedContent from the initial value", () => {
    const { result } = renderHook(() => useEditorState("hello"));
    expect(result.current.editorContent).toBe("hello");
    expect(result.current.savedContent).toBe("hello");
    expect(result.current.isDirty).toBe(false);
  });

  it("flags isDirty when the editor diverges from savedContent", () => {
    const { result } = renderHook(() => useEditorState("a"));

    act(() => result.current.setEditorContent("a-edited"));
    expect(result.current.isDirty).toBe(true);
    expect(result.current.effectiveSaveStatus).toBe("unsaved");

    act(() => result.current.setSavedContent("a-edited"));
    expect(result.current.isDirty).toBe(false);
    expect(result.current.effectiveSaveStatus).toBe("idle");
  });

  it("prefers explicit save statuses over the dirty-derived 'unsaved' status", () => {
    const { result } = renderHook(() => useEditorState("a"));

    act(() => {
      result.current.setEditorContent("dirty");
      result.current.setSaveStatus("saving");
    });
    expect(result.current.effectiveSaveStatus).toBe("saving");

    act(() => result.current.setSaveStatus("error"));
    expect(result.current.effectiveSaveStatus).toBe("error");
  });
});
