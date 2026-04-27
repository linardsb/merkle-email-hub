import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useRef } from "react";

import { useWorkspaceFollowMode } from "../use-workspace-follow-mode";
import type { Collaborator } from "@/types/collaboration";
import type { CodeEditorHandle } from "@/hooks/use-editor-bridge";

function makeEditorHandle(revealLineInCenter: ReturnType<typeof vi.fn>): CodeEditorHandle {
  const model = { getLineCount: () => 100 };
  const editor = {
    getModel: () => model,
    revealLineInCenter,
  } as unknown as ReturnType<CodeEditorHandle["getEditor"]>;
  return { getEditor: () => editor };
}

function makeCollaborator(line: number): Collaborator {
  return {
    clientId: 7,
    name: "Bob",
    color: "#fff",
    role: "developer",
    cursor: { line, col: 0 },
    selection: null,
    activity: "editing",
    lastActiveAt: Date.now(),
  };
}

describe("useWorkspaceFollowMode", () => {
  it("does nothing when there is no follow target", () => {
    const reveal = vi.fn();
    const { result: editorRef } = renderHook(() =>
      useRef<CodeEditorHandle | null>(makeEditorHandle(reveal)),
    );

    renderHook(() =>
      useWorkspaceFollowMode({
        followTarget: null,
        collaborators: [makeCollaborator(5)],
        editorRef: editorRef.current,
      }),
    );

    expect(reveal).not.toHaveBeenCalled();
  });

  it("reveals the followed user's cursor line when target moves", () => {
    const reveal = vi.fn();
    const { result: editorRef } = renderHook(() =>
      useRef<CodeEditorHandle | null>(makeEditorHandle(reveal)),
    );

    renderHook(() =>
      useWorkspaceFollowMode({
        followTarget: { clientId: 7 },
        collaborators: [makeCollaborator(42)],
        editorRef: editorRef.current,
      }),
    );

    expect(reveal).toHaveBeenCalledWith(42);
  });

  it("clamps the line number to the model's line count", () => {
    const reveal = vi.fn();
    const { result: editorRef } = renderHook(() =>
      useRef<CodeEditorHandle | null>(makeEditorHandle(reveal)),
    );

    renderHook(() =>
      useWorkspaceFollowMode({
        followTarget: { clientId: 7 },
        collaborators: [makeCollaborator(9999)],
        editorRef: editorRef.current,
      }),
    );

    expect(reveal).toHaveBeenCalledWith(100);
  });
});
