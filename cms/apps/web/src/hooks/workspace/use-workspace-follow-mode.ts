"use client";

import { useEffect, useRef } from "react";
import type { RefObject } from "react";
import type { Collaborator } from "@/types/collaboration";
import type { CodeEditorHandle } from "@/hooks/use-editor-bridge";

interface FollowMode {
  followTarget: { clientId: number } | null;
  collaborators: Collaborator[];
  editorRef: RefObject<CodeEditorHandle | null>;
}

/**
 * Scrolls the Monaco editor to the followed user's cursor line whenever the
 * follow target moves to a new line. No-op when no target is set.
 */
export function useWorkspaceFollowMode({ followTarget, collaborators, editorRef }: FollowMode) {
  const lastFollowLineRef = useRef<number | null>(null);

  useEffect(() => {
    if (!followTarget) {
      lastFollowLineRef.current = null;
      return;
    }
    const target = collaborators.find((c) => c.clientId === followTarget.clientId);
    if (!target?.cursor) return;

    if (target.cursor.line === lastFollowLineRef.current) return;
    lastFollowLineRef.current = target.cursor.line;

    const editor = editorRef.current?.getEditor?.();
    if (!editor) return;

    const model = editor.getModel();
    if (!model) return;
    const lineNum = Math.min(target.cursor.line, model.getLineCount());
    editor.revealLineInCenter(lineNum);
  }, [followTarget, collaborators, editorRef]);
}
