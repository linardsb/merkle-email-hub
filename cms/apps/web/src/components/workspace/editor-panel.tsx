"use client";

import { forwardRef, useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { CodeEditorHandle } from "@/hooks/use-editor-bridge";
import type { SaveStatus } from "./save-indicator";
import type { BrandConfig } from "@/types/brand";
import type { Doc as YDoc } from "yjs";
import type { Awareness } from "y-protocols/awareness";
import type { SyncStatus } from "@/types/visual-builder";
import { useBuilderSync } from "@/hooks/use-builder-sync";

const CodeEditor = dynamic(
  () =>
    import("@/components/workspace/editor/code-editor").then(
      (mod) => mod.CodeEditor
    ),
  {
    ssr: false,
    loading: () => <EditorLoading />,
  }
);

const VisualBuilderPanel = dynamic(
  () =>
    import("@/components/builder/visual-builder-panel").then(
      (mod) => mod.VisualBuilderPanel
    ),
  {
    ssr: false,
    loading: () => <EditorLoading />,
  }
);

function EditorLoading() {
  return (
    <div className="flex h-full items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      <span className="ml-2 text-sm text-muted-foreground">
        {"Loading editor..."}
      </span>
    </div>
  );
}

const SYNC_STATUS_COLORS: Record<SyncStatus, string> = {
  synced: "bg-success",
  syncing: "bg-warning animate-pulse",
  parse_error: "bg-destructive",
  conflict: "bg-destructive",
};

type EditorTab = "code" | "builder" | "split";

interface EditorPanelProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saveStatus?: SaveStatus;
  readOnly?: boolean;
  brandConfig?: BrandConfig | null;
  onBrandViolationsChange?: (count: number) => void;
  onCursorOffsetChange?: (offset: number) => void;
  onSelectionChange?: (hasSelection: boolean) => void;
  collaborative?: {
    doc: YDoc;
    awareness: Awareness;
    user: { name: string; color: string; role: string };
    fieldName?: string;
  };
  projectId?: number;
}

export const EditorPanel = forwardRef<CodeEditorHandle, EditorPanelProps>(function EditorPanel({ value, onChange, onSave, saveStatus, readOnly, brandConfig, onBrandViolationsChange, onCursorOffsetChange, onSelectionChange, collaborative, projectId }: EditorPanelProps, ref) {
  // Persist view mode per project in localStorage
  const storageKey = projectId ? `editor-view-${projectId}` : null;
  const [activeTab, setActiveTab] = useState<EditorTab>(() => {
    if (typeof window === "undefined" || !storageKey) return "code";
    const stored = localStorage.getItem(storageKey);
    if (stored === "code" || stored === "builder" || stored === "split") return stored;
    return "code";
  });

  useEffect(() => {
    if (storageKey) localStorage.setItem(storageKey, activeTab);
  }, [activeTab, storageKey]);

  // Sync engine — only active in split mode
  const isSplit = activeTab === "split";
  const {
    syncStatus,
    parseError,
    handleCodeChange: syncCodeChange,
    parsedSections,
    serializedHtml,
    dismissParseError,
  } = useBuilderSync({ enabled: isSplit });

  // When sync engine produces new HTML from builder changes, push to parent
  useEffect(() => {
    if (serializedHtml !== null && isSplit) {
      onChange(serializedHtml);
    }
  }, [serializedHtml, isSplit, onChange]);

  // Wrap onChange to also feed sync engine in split mode
  const handleSyncedCodeChange = useCallback(
    (html: string) => {
      onChange(html);
      if (isSplit) syncCodeChange(html);
    },
    [onChange, isSplit, syncCodeChange]
  );

  // Builder code change handler for split mode (builder -> code via sync)
  const handleSyncedBuilderChange = useCallback(
    (html: string) => {
      // In split mode, builder HTML changes are handled by sync engine
      // For non-split mode, pass through directly
      if (!isSplit) onChange(html);
    },
    [isSplit, onChange]
  );

  const tabClasses = (tab: EditorTab) =>
    `px-4 py-1.5 text-xs font-medium transition-colors ${
      activeTab === tab
        ? "border-b-2 border-interactive text-foreground"
        : "text-muted-foreground hover:text-foreground"
    }`;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Tab bar */}
      <div className="flex items-center border-b border-default bg-surface">
        <button type="button" onClick={() => setActiveTab("code")} className={tabClasses("code")}>
          {"Code"}
        </button>
        <button type="button" onClick={() => setActiveTab("builder")} className={tabClasses("builder")}>
          {"Builder"}
        </button>
        <button type="button" onClick={() => setActiveTab("split")} className={tabClasses("split")}>
          {"Split"}
        </button>

        {/* Sync status indicator (split mode only) */}
        {isSplit && (
          <div className="ml-2 flex items-center gap-1.5">
            <div className={`h-1.5 w-1.5 rounded-full ${SYNC_STATUS_COLORS[syncStatus]}`} />
            {syncStatus === "parse_error" && (
              <span className="text-[10px] text-destructive">{"Parse error"}</span>
            )}
          </div>
        )}
      </div>

      {/* Parse error banner (split mode) */}
      {isSplit && parseError && (
        <div className="flex items-center gap-2 border-b border-border bg-muted px-3 py-1.5 text-xs text-muted-foreground">
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-destructive" />
          <span className="flex-1">{parseError}</span>
          <button
            type="button"
            onClick={dismissParseError}
            className="text-xs text-muted-foreground underline hover:text-foreground"
          >
            {"Dismiss"}
          </button>
        </div>
      )}

      {/* Panel content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "code" && (
          <CodeEditor
            ref={ref}
            value={value}
            onChange={onChange}
            onSave={onSave}
            saveStatus={saveStatus}
            readOnly={readOnly}
            brandConfig={brandConfig}
            onBrandViolationsChange={onBrandViolationsChange}
            onCursorOffsetChange={onCursorOffsetChange}
            onSelectionChange={onSelectionChange}
            collaborative={collaborative}
          />
        )}

        {activeTab === "builder" && (
          <VisualBuilderPanel code={value} onCodeChange={onChange} projectId={projectId} />
        )}

        {activeTab === "split" && (
          <div className="flex h-full overflow-hidden">
            <div className="w-1/2 border-r border-default overflow-hidden">
              <CodeEditor
                ref={ref}
                value={value}
                onChange={handleSyncedCodeChange}
                onSave={onSave}
                saveStatus={saveStatus}
                readOnly={readOnly}
                brandConfig={brandConfig}
                onBrandViolationsChange={onBrandViolationsChange}
                onCursorOffsetChange={onCursorOffsetChange}
                onSelectionChange={onSelectionChange}
                collaborative={collaborative}
              />
            </div>
            <div className="w-1/2 overflow-hidden">
              <VisualBuilderPanel
                code={value}
                onCodeChange={handleSyncedBuilderChange}
                projectId={projectId}
                syncedSections={parsedSections}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
});
