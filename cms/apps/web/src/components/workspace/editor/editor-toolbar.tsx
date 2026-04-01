"use client";

import { AlertTriangle, WrapText, Palette } from "../../icons";
import { SaveIndicator, type SaveStatus } from "../save-indicator";
import { EDITOR_THEMES } from "./editor-themes";

interface EditorToolbarProps {
  line: number;
  col: number;
  warningCount: number;
  wordWrapEnabled: boolean;
  saveStatus: SaveStatus;
  onToggleWordWrap: () => void;
  editorThemeId?: string;
  onEditorThemeChange?: (themeId: string) => void;
}

export function EditorToolbar({
  line,
  col,
  warningCount,
  wordWrapEnabled,
  saveStatus,
  onToggleWordWrap,
  editorThemeId,
  onEditorThemeChange,
}: EditorToolbarProps) {
  return (
    <div className="flex h-8 items-center justify-between border-b border-border bg-card px-3 text-xs text-muted-foreground">
      <div className="flex items-center gap-3">
        {warningCount > 0 && (
          <span className="flex items-center gap-1 text-destructive">
            <AlertTriangle className="h-3 w-3" />
            {`${warningCount} CSS ${warningCount === 1 ? "warning" : "warnings"}`}
          </span>
        )}
        <SaveIndicator status={saveStatus} />
      </div>

      <div className="flex items-center gap-2">
        <span>{`Ln ${line}, Col ${col}`}</span>

        {onEditorThemeChange && (
          <div className="flex items-center gap-1">
            <Palette className="h-3.5 w-3.5" />
            <select
              value={editorThemeId}
              onChange={(e) => onEditorThemeChange(e.target.value)}
              className="h-6 rounded border border-border bg-card px-1 text-xs text-foreground outline-none focus:ring-1 focus:ring-ring"
            >
              {EDITOR_THEMES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          type="button"
          onClick={onToggleWordWrap}
          className={`rounded p-1 transition-colors hover:bg-accent ${wordWrapEnabled ? "text-foreground" : ""}`}
          title={"Toggle word wrap"}
        >
          <WrapText className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
