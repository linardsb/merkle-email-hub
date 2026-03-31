"use client";

import { useCallback, useState } from "react";
import { MessageSquare, Zap, Layers, History } from "lucide-react";
import { ChatPanel } from "./chat-panel";
import { BlueprintRunsList } from "./blueprint/runs-list";
import { AgentContextPanel } from "./agent-context-panel";
import { VersionHistoryPanel } from "./version-history-panel";
import { useBlueprintRun } from "@/hooks/use-blueprint-run";
import type { AgentMode } from "@/types/chat";
import type { BlueprintRunRecord } from "@/types/blueprint-runs";

type BottomPanelTab = "chat" | "runs" | "context" | "history";

interface BottomPanelProps {
  projectId: string;
  projectIdNum: number;
  onApplyToEditor?: (html: string) => void;
  initialAgent?: AgentMode;
  editorContent?: string;
  templateId?: number | null;
  currentVersionNumber?: number | null;
  onRestoreVersion?: (html: string, versionNumber: number) => void;
}

export function BottomPanel({
  projectId,
  projectIdNum,
  onApplyToEditor,
  initialAgent,
  editorContent,
  templateId,
  currentVersionNumber,
  onRestoreVersion,
}: BottomPanelProps) {
  const [activeTab, setActiveTab] = useState<BottomPanelTab>("chat");
  const { resume, isRunning, error } = useBlueprintRun({ projectId: projectIdNum });
  const [resumingRun, setResumingRun] = useState<BlueprintRunRecord | null>(null);

  const handleResumeRun = useCallback(async (run: BlueprintRunRecord) => {
    setResumingRun(run);
    const res = await resume({
      run_id: run.run_data?.run_id ?? String(run.id),
      blueprint_name: run.blueprint_name,
      brief: run.brief_excerpt,
    });
    if (res?.html && onApplyToEditor) {
      onApplyToEditor(res.html);
    }
    // Only clear resumingRun on success so the error banner stays visible on failure
    if (res) {
      setResumingRun(null);
    }
  }, [resume, onApplyToEditor]);

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border bg-muted/50 px-2 pt-1" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "chat"}
          onClick={() => setActiveTab("chat")}
          className={`flex cursor-pointer items-center gap-1.5 rounded-t-md px-3 py-1.5 text-xs font-medium transition-all ${
            activeTab === "chat"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          {"AI Chat"}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "runs"}
          onClick={() => setActiveTab("runs")}
          className={`flex cursor-pointer items-center gap-1.5 rounded-t-md px-3 py-1.5 text-xs font-medium transition-all ${
            activeTab === "runs"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <Zap className="h-3.5 w-3.5" />
          {"Blueprint Runs"}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "context"}
          onClick={() => setActiveTab("context")}
          className={`flex cursor-pointer items-center gap-1.5 rounded-t-md px-3 py-1.5 text-xs font-medium transition-all ${
            activeTab === "context"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          {"Context"}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
          className={`flex cursor-pointer items-center gap-1.5 rounded-t-md px-3 py-1.5 text-xs font-medium transition-all ${
            activeTab === "history"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <History className="h-3.5 w-3.5" />
          {"History"}
        </button>
      </div>

      {/* Resume status banner */}
      {isRunning && resumingRun && (
        <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-3 py-2">
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted border-t-primary" />
          <span className="text-xs text-muted-foreground">{"Resuming from checkpoint..."}</span>
        </div>
      )}

      {error && resumingRun && (
        <div className="border-b border-destructive/20 bg-destructive/5 px-3 py-2">
          <span className="text-xs text-destructive">{"Failed to resume run. Please try again."}</span>
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "chat" ? (
          <ChatPanel
            projectId={projectId}
            onApplyToEditor={onApplyToEditor}
            initialAgent={initialAgent}
            editorContent={editorContent}
          />
        ) : activeTab === "runs" ? (
          <BlueprintRunsList
            projectId={projectIdNum}
            onApplyResult={onApplyToEditor}
            onResumeRun={handleResumeRun}
          />
        ) : activeTab === "history" ? (
          <VersionHistoryPanel
            templateId={templateId ?? null}
            currentVersionNumber={currentVersionNumber ?? null}
            onRestore={onRestoreVersion ?? (() => {})}
          />
        ) : (
          <AgentContextPanel
            projectId={projectIdNum}
            editorContent={editorContent ?? ""}
          />
        )}
      </div>
    </div>
  );
}
