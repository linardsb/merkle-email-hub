"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, WrapText } from "lucide-react";
import { SaveIndicator, type SaveStatus } from "../save-indicator";

interface EditorToolbarProps {
  line: number;
  col: number;
  warningCount: number;
  wordWrapEnabled: boolean;
  saveStatus: SaveStatus;
  onToggleWordWrap: () => void;
}

export function EditorToolbar({
  line,
  col,
  warningCount,
  wordWrapEnabled,
  saveStatus,
  onToggleWordWrap,
}: EditorToolbarProps) {
  const t = useTranslations("workspace");

  return (
    <div className="flex h-8 items-center justify-between border-b border-border bg-card px-3 text-xs text-muted-foreground">
      <div className="flex items-center gap-3">
        <span>{t("editorLanguage")}</span>
        {warningCount > 0 && (
          <span className="flex items-center gap-1 text-destructive">
            <AlertTriangle className="h-3 w-3" />
            {t("editorCssWarningCount", { count: warningCount })}
          </span>
        )}
        <SaveIndicator status={saveStatus} />
      </div>

      <div className="flex items-center gap-2">
        <span>{t("editorLineCol", { line, col })}</span>

        <button
          type="button"
          onClick={onToggleWordWrap}
          className={`rounded p-1 transition-colors hover:bg-accent ${wordWrapEnabled ? "text-foreground" : ""}`}
          title={t("editorWordWrap")}
        >
          <WrapText className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
