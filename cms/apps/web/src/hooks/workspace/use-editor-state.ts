"use client";

import { useRef, useState } from "react";
import type { SaveStatus } from "@/components/workspace/save-indicator";

/**
 * Owns the editor's text buffer, the last-saved snapshot, the save-status
 * indicator, and refs that coordinate with the auto-save timer + image-gen
 * cursor insertion. The dirty flag is derived (not stored) so it stays in
 * sync with both buffers without an extra effect.
 */
export function useEditorState(initialContent: string) {
  const [editorContent, setEditorContent] = useState(initialContent);
  const [savedContent, setSavedContent] = useState(initialContent);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cursorOffsetRef = useRef<number>(0);

  const isDirty = editorContent !== savedContent;

  const effectiveSaveStatus: SaveStatus =
    saveStatus === "saving"
      ? "saving"
      : saveStatus === "error"
        ? "error"
        : saveStatus === "saved"
          ? "saved"
          : isDirty
            ? "unsaved"
            : "idle";

  return {
    editorContent,
    setEditorContent,
    savedContent,
    setSavedContent,
    saveStatus,
    setSaveStatus,
    isDirty,
    effectiveSaveStatus,
    savedTimerRef,
    cursorOffsetRef,
  };
}
