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
    <div className="border-border bg-card text-muted-foreground flex h-8 items-center justify-between border-b px-3 text-xs">
      <div className="flex items-center gap-3">
        {warningCount > 0 && (
          <span className="text-destructive flex items-center gap-1">
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
              className="border-border bg-card text-foreground focus:ring-ring h-6 rounded border px-1 text-xs outline-none focus:ring-1"
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
          className={`hover:bg-accent rounded p-1 transition-colors ${wordWrapEnabled ? "text-foreground" : ""}`}
          title={"Toggle word wrap"}
        >
          <WrapText className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
