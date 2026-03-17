"use client";

import { useEffect } from "react";

interface WorkspaceShortcuts {
  onSave?: () => void;
  onGenerate?: () => void;
  onRunQA?: () => void;
  onExport?: () => void;
  onToggleChat?: () => void;
  onToggleSidebar?: () => void;
}

export function useWorkspaceShortcuts({
  onSave,
  onGenerate,
  onRunQA,
  onExport,
  onToggleChat,
  onToggleSidebar,
}: WorkspaceShortcuts) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;

      // Cmd+S — Save (already handled by editor, but catch globally too)
      if (e.key === "s" && !e.shiftKey) {
        e.preventDefault();
        onSave?.();
        return;
      }

      // Cmd+Shift+G — Generate Blueprint
      if (e.key === "g" && e.shiftKey) {
        e.preventDefault();
        onGenerate?.();
        return;
      }

      // Cmd+Shift+Q — Run QA
      if (e.key === "q" && e.shiftKey) {
        e.preventDefault();
        onRunQA?.();
        return;
      }

      // Cmd+Shift+E — Export
      if (e.key === "e" && e.shiftKey) {
        e.preventDefault();
        onExport?.();
        return;
      }

      // Cmd+B — Toggle bottom panel (chat)
      if (e.key === "b" && !e.shiftKey) {
        e.preventDefault();
        onToggleChat?.();
        return;
      }

      // Cmd+J — Toggle sidebar
      if (e.key === "j" && !e.shiftKey) {
        e.preventDefault();
        onToggleSidebar?.();
        return;
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onSave, onGenerate, onRunQA, onExport, onToggleChat, onToggleSidebar]);
}
