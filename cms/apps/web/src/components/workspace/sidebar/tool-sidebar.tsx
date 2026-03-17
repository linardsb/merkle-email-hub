"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ShieldCheck, FlaskConical, Monitor, Brain, X } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@email-hub/ui/components/ui/tooltip";
import { QATab } from "./qa-tab";
import { TestingTab } from "./testing-tab";
import { EmailClientsTab } from "./email-clients-tab";
import { IntelligenceTab } from "./intelligence-tab";
import type { QAResultResponse } from "@/types/qa";
import type { VisualQAEntityType } from "@/types/rendering";

type SidebarTab = "qa" | "testing" | "clients" | "intelligence";

const TABS: { id: SidebarTab; icon: React.ComponentType<{ className?: string }>; labelKey: string }[] = [
  { id: "qa", icon: ShieldCheck, labelKey: "tabQA" },
  { id: "testing", icon: FlaskConical, labelKey: "tabTesting" },
  { id: "clients", icon: Monitor, labelKey: "tabClients" },
  { id: "intelligence", icon: Brain, labelKey: "tabIntelligence" },
];

interface ToolSidebarProps {
  result: QAResultResponse;
  onClose: () => void;
  onOverrideSuccess: () => void;
  html?: string;
  entityType?: VisualQAEntityType;
  entityId?: number;
  onHtmlUpdate?: (html: string) => void;
}

export function ToolSidebar({
  result,
  onClose,
  onOverrideSuccess,
  html,
  entityType,
  entityId,
  onHtmlUpdate,
}: ToolSidebarProps) {
  const t = useTranslations("workspace.sidebarTabs");
  const [activeTab, setActiveTab] = useState<SidebarTab>("qa");

  return (
    <div className="flex h-full w-80 flex-col border-l border-border bg-card">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border">
        <TooltipProvider delayDuration={300}>
          <div className="flex flex-1 items-center">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <Tooltip key={tab.id}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex flex-1 items-center justify-center py-2.5 transition-colors ${
                        isActive
                          ? "border-b-2 border-primary text-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom" className="text-xs">
                    {t(tab.labelKey)}
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </div>
        </TooltipProvider>
        <button
          type="button"
          onClick={onClose}
          aria-label={t("close")}
          className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground mr-1"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Tab content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {activeTab === "qa" && (
          <QATab result={result} onOverrideSuccess={onOverrideSuccess} />
        )}
        {activeTab === "testing" && (
          <TestingTab html={html} entityType={entityType} entityId={entityId} />
        )}
        {activeTab === "clients" && (
          <EmailClientsTab html={html} onHtmlUpdate={onHtmlUpdate} />
        )}
        {activeTab === "intelligence" && <IntelligenceTab />}
      </div>
    </div>
  );
}
