"use client";

import { useState } from "react";
import { Blocks } from "../../../components/icons";
import {
  EcosystemDashboard,
  PluginManagerPanel,
  WorkflowPanel,
  ReportPanel,
  PenpotPanel,
} from "@/components/ecosystem";
import { TranslationPanel } from "@/components/tolgee";
import { useTolgeeConnection } from "@/hooks/use-tolgee";
import type { EcosystemTab } from "@/types/ecosystem";

const TABS: { id: EcosystemTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "plugins", label: "Plugins" },
  { id: "workflows", label: "Workflows" },
  { id: "translations", label: "Translations" },
  { id: "reports", label: "Reports" },
  { id: "penpot", label: "Penpot" },
];

export default function EcosystemPage() {
  const [activeTab, setActiveTab] = useState<EcosystemTab>("overview");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Blocks className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Ecosystem</h1>
        </div>
        <p className="mt-1 text-sm text-foreground-muted">
          Manage plugins, workflows, translations, reports, and design integrations.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-interactive text-foreground-inverse"
                : "text-foreground-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && <EcosystemDashboard onNavigate={setActiveTab} />}
      {activeTab === "plugins" && <PluginManagerPanel />}
      {activeTab === "workflows" && <WorkflowPanel />}
      {activeTab === "translations" && <TranslationsTab />}
      {activeTab === "reports" && <ReportPanel />}
      {activeTab === "penpot" && <PenpotPanel />}
    </div>
  );
}

function TranslationsTab() {
  const { data: connection, isLoading } = useTolgeeConnection(1);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="h-8 w-48 animate-pulse rounded bg-surface-hover" />
        <div className="h-64 animate-pulse rounded-lg border border-card-border bg-card-bg" />
      </div>
    );
  }

  if (!connection || connection.tolgee_project_id === null) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg p-8 text-center">
        <p className="text-foreground-muted">
          No Tolgee connection configured. Set up a connection in the Connectors page.
        </p>
      </div>
    );
  }

  return (
    <TranslationPanel
      connectionId={connection.id}
      tolgeeProjectId={connection.tolgee_project_id}
      templateId={1}
      languages={[]}
      onTranslationEdit={() => {}}
    />
  );
}
