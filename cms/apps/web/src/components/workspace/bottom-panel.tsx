"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { MessageSquare, Zap } from "lucide-react";
import { ChatPanel } from "./chat-panel";
import { BlueprintRunsList } from "./blueprint/runs-list";
import type { AgentMode } from "@/types/chat";

type BottomPanelTab = "chat" | "runs";

interface BottomPanelProps {
  projectId: string;
  projectIdNum: number;
  onApplyToEditor?: (html: string) => void;
  initialAgent?: AgentMode;
}

export function BottomPanel({
  projectId,
  projectIdNum,
  onApplyToEditor,
  initialAgent,
}: BottomPanelProps) {
  const t = useTranslations("workspace");
  const [activeTab, setActiveTab] = useState<BottomPanelTab>("chat");

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
          {t("chatTabLabel")}
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
          {t("runsTabLabel")}
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "chat" ? (
          <ChatPanel
            projectId={projectId}
            onApplyToEditor={onApplyToEditor}
            initialAgent={initialAgent}
          />
        ) : (
          <BlueprintRunsList
            projectId={projectIdNum}
            onApplyResult={onApplyToEditor}
          />
        )}
      </div>
    </div>
  );
}
