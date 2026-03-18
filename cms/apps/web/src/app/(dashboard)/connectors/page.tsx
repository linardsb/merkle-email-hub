"use client";

import { useState, useMemo, useCallback } from "react";
import { Plug, Plus } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { EmptyState } from "@/components/ui/empty-state";
import { useExportHistory } from "@/hooks/use-export-history";
import { ExportCard } from "@/components/connectors/export-card";
import { ESPConnectionCard } from "@/components/connectors/esp-connection-card";
import { ESPTemplateBrowser } from "@/components/connectors/esp-template-browser";
import { ESPTemplatePreviewDialog } from "@/components/connectors/esp-template-preview-dialog";
import { CreateESPConnectionDialog } from "@/components/connectors/create-esp-connection-dialog";
import { useESPConnections, useImportESPTemplate } from "@/hooks/use-esp-sync";
import { authFetch } from "@/lib/auth-fetch";
import type { ConnectorPlatform } from "@/types/connectors";
import type { ESPTemplate } from "@/types/esp-sync";

const PLATFORM_FILTERS = ["all", "braze", "sfmc", "adobe_campaign", "taxi", "raw_html"] as const;

const PLATFORM_LABELS: Record<string, string> = {
  all: "All",
  braze: "Braze",
  sfmc: "SFMC",
  adobe_campaign: "Adobe Campaign",
  taxi: "Taxi",
  raw_html: "Raw HTML",
};

const ESP_FILTERS = ["all", "braze", "sfmc", "adobe_campaign", "taxi"] as const;

const ESP_LABELS: Record<string, string> = {
  all: "All",
  braze: "Braze",
  sfmc: "SFMC",
  adobe_campaign: "Adobe Campaign",
  taxi: "Taxi",
};

type PageTab = "export-history" | "esp-sync";

export default function ConnectorsPage() {
  const { mutate: globalMutate } = useSWRConfig();
  const { records } = useExportHistory();
  const { data: espConnections } = useESPConnections();

  // Tab state
  const [activeTab, setActiveTab] = useState<PageTab>("export-history");

  // Export History filter
  const [activeFilter, setActiveFilter] = useState<string>("all");

  // ESP Sync state
  const [espFilter, setEspFilter] = useState<string>("all");
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [previewTemplate, setPreviewTemplate] = useState<ESPTemplate | null>(null);
  const [importingTemplateId, setImportingTemplateId] = useState<string | null>(null);

  // Hooks for mutations
  const { trigger: triggerImport } = useImportESPTemplate(selectedConnectionId);

  // Filtered export records
  const filteredRecords = useMemo(() => {
    if (activeFilter === "all") return records;
    return records.filter(
      (r) => r.platform === (activeFilter as ConnectorPlatform)
    );
  }, [records, activeFilter]);

  // Filtered ESP connections
  const filteredConnections = useMemo(() => {
    const conns = espConnections ?? [];
    if (espFilter === "all") return conns;
    return conns.filter((c) => c.esp_type === espFilter);
  }, [espConnections, espFilter]);

  const selectedConnection = (espConnections ?? []).find((c) => c.id === selectedConnectionId) ?? null;

  // Import handler
  const handleImport = useCallback(async (templateId: string) => {
    if (!selectedConnectionId) return;
    setImportingTemplateId(templateId);
    try {
      await triggerImport({ template_id: templateId });
      toast.success("Template imported successfully");
    } catch {
      toast.error("Failed to import template");
    } finally {
      setImportingTemplateId(null);
    }
  }, [selectedConnectionId, triggerImport]);

  // Delete handler — uses authFetch directly to avoid hook URL race condition
  const handleDelete = useCallback(async (connectionId: number) => {
    if (!confirm("Delete this connection? This cannot be undone.")) return;
    try {
      const res = await authFetch(`/api/v1/connectors/sync/connections/${connectionId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      await globalMutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/connectors/sync"),
        undefined,
        { revalidate: true },
      );
      toast.success("Connection deleted");
      if (selectedConnectionId === connectionId) {
        setSelectedConnectionId(null);
      }
    } catch {
      toast.error("Failed to delete connection");
    }
  }, [globalMutate, selectedConnectionId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Plug className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold text-foreground">{"Connectors & Exports"}</h1>
        </div>
        {activeTab === "esp-sync" && (
          <button
            type="button"
            onClick={() => setCreateDialogOpen(true)}
            className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            <Plus className="h-4 w-4" />
            {"Add Connection"}
          </button>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
        <button
          type="button"
          onClick={() => setActiveTab("export-history")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            activeTab === "export-history"
              ? "bg-interactive text-foreground-inverse"
              : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          }`}
        >
          {"Export History"}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("esp-sync")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            activeTab === "esp-sync"
              ? "bg-interactive text-foreground-inverse"
              : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
          }`}
        >
          {"ESP Sync"}
        </button>
      </div>

      {/* Export History Tab */}
      {activeTab === "export-history" && (
        <>
          {/* Platform filter tabs */}
          <div className="flex gap-2">
            {PLATFORM_FILTERS.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setActiveFilter(filter)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  activeFilter === filter
                    ? "bg-interactive text-foreground-inverse"
                    : "bg-surface-muted text-foreground-muted hover:text-foreground"
                }`}
              >
                {PLATFORM_LABELS[filter] ?? "All"}
              </button>
            ))}
          </div>

          {filteredRecords.length === 0 ? (
            <EmptyState
              icon={Plug}
              title={"No exports yet"}
              description={"Export history will appear here when you export from the workspace."}
            />
          ) : (
            <div className="animate-fade-in grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredRecords.map((record) => (
                <ExportCard key={record.local_id} record={record} />
              ))}
            </div>
          )}
        </>
      )}

      {/* ESP Sync Tab */}
      {activeTab === "esp-sync" && (
        <>
          {/* ESP filter tabs */}
          <div className="flex gap-2">
            {ESP_FILTERS.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => setEspFilter(filter)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  espFilter === filter
                    ? "bg-interactive text-foreground-inverse"
                    : "bg-surface-muted text-foreground-muted hover:text-foreground"
                }`}
              >
                {ESP_LABELS[filter] ?? "All"}
              </button>
            ))}
          </div>

          {/* Connection cards */}
          {filteredConnections.length === 0 ? (
            <EmptyState
              icon={Plug}
              title={"No ESP connections"}
              description={"Connect to Braze, SFMC, Adobe Campaign, or Taxi to sync templates"}
              action={
                <button
                  type="button"
                  onClick={() => setCreateDialogOpen(true)}
                  className="mt-2 flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
                >
                  <Plus className="h-4 w-4" />
                  {"Add Connection"}
                </button>
              }
            />
          ) : (
            <div className="animate-fade-in grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredConnections.map((conn) => (
                <ESPConnectionCard
                  key={conn.id}
                  connection={conn}
                  selected={selectedConnectionId === conn.id}
                  onSelect={() =>
                    setSelectedConnectionId(
                      selectedConnectionId === conn.id ? null : conn.id
                    )
                  }
                  onDelete={() => handleDelete(conn.id)}
                />
              ))}
            </div>
          )}

          {/* Template browser (shown when connection is selected) */}
          {selectedConnection && (
            <div className="rounded-lg border border-card-border bg-card-bg p-4">
              <ESPTemplateBrowser
                connectionId={selectedConnection.id}
                espType={selectedConnection.esp_type}
                onPreview={(tpl) => setPreviewTemplate(tpl)}
                onImport={handleImport}
                importing={importingTemplateId}
              />
            </div>
          )}
        </>
      )}

      {/* Dialogs */}
      <CreateESPConnectionDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />

      <ESPTemplatePreviewDialog
        open={previewTemplate !== null}
        onOpenChange={(open) => { if (!open) setPreviewTemplate(null); }}
        template={previewTemplate}
        onImport={handleImport}
        importing={importingTemplateId !== null}
      />
    </div>
  );
}
