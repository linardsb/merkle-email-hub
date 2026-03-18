"use client";

import { useCallback, useState } from "react";
import {
  mergeSections,
  splitSection,
  unwrapSection,
  renameSection,
} from "@/lib/builder-sync/annotation-utils";

interface SectionRefinementToolbarProps {
  html: string;
  selectedSectionIds: string[];
  selectedSectionName?: string;
  onHtmlChange: (html: string) => void;
}

export function SectionRefinementToolbar({
  html,
  selectedSectionIds,
  selectedSectionName,
  onHtmlChange,
}: SectionRefinementToolbarProps) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(selectedSectionName ?? "");

  const singleSelected = selectedSectionIds.length === 1;
  const multiSelected = selectedSectionIds.length >= 2;

  const handleMerge = useCallback(() => {
    if (!multiSelected) return;
    const updated = mergeSections(html, selectedSectionIds);
    onHtmlChange(updated);
  }, [html, selectedSectionIds, multiSelected, onHtmlChange]);

  const handleSplit = useCallback(() => {
    const id = selectedSectionIds[0];
    if (!singleSelected || !id) return;
    const updated = splitSection(html, id, 1);
    onHtmlChange(updated);
  }, [html, selectedSectionIds, singleSelected, onHtmlChange]);

  const handleUnwrap = useCallback(() => {
    const id = selectedSectionIds[0];
    if (!singleSelected || !id) return;
    const updated = unwrapSection(html, id);
    onHtmlChange(updated);
  }, [html, selectedSectionIds, singleSelected, onHtmlChange]);

  const handleRename = useCallback(() => {
    const id = selectedSectionIds[0];
    if (!singleSelected || !id || !renameValue.trim()) return;
    const updated = renameSection(html, id, renameValue.trim());
    onHtmlChange(updated);
    setIsRenaming(false);
  }, [html, selectedSectionIds, singleSelected, renameValue, onHtmlChange]);

  if (selectedSectionIds.length === 0) return null;

  return (
    <div className="flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 shadow-sm">
      {/* Merge (multi-select) */}
      <button
        onClick={handleMerge}
        disabled={!multiSelected}
        className="rounded px-2 py-0.5 text-[10px] font-medium text-foreground hover:bg-accent disabled:opacity-30"
        title="Merge selected sections"
      >
        Merge
      </button>

      {/* Split (single select) */}
      <button
        onClick={handleSplit}
        disabled={!singleSelected}
        className="rounded px-2 py-0.5 text-[10px] font-medium text-foreground hover:bg-accent disabled:opacity-30"
        title="Split section"
      >
        Split
      </button>

      {/* Unwrap (single select) */}
      <button
        onClick={handleUnwrap}
        disabled={!singleSelected}
        className="rounded px-2 py-0.5 text-[10px] font-medium text-foreground hover:bg-accent disabled:opacity-30"
        title="Remove section annotation"
      >
        Unwrap
      </button>

      {/* Rename (single select) */}
      <div className="border-l border-border pl-1">
        {isRenaming ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleRename();
            }}
            className="flex items-center gap-1"
          >
            <input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              className="w-20 rounded border border-input bg-background px-1.5 py-0.5 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              autoFocus
              onBlur={() => setIsRenaming(false)}
            />
          </form>
        ) : (
          <button
            onClick={() => {
              setRenameValue(selectedSectionName ?? "");
              setIsRenaming(true);
            }}
            disabled={!singleSelected}
            className="rounded px-2 py-0.5 text-[10px] font-medium text-foreground hover:bg-accent disabled:opacity-30"
            title="Rename section"
          >
            Rename
          </button>
        )}
      </div>
    </div>
  );
}
