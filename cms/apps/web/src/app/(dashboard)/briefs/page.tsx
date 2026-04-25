"use client";

import { useState } from "react";
import { ClipboardList } from "../../../components/icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { EmptyState } from "@/components/ui/empty-state";
import { BriefConnectionCard } from "@/components/briefs/brief-connection-card";
import { BriefItemsPanel } from "@/components/briefs/brief-items-panel";
import { ConnectBriefDialog } from "@/components/briefs/connect-brief-dialog";
import { BriefImportDialog } from "@/components/briefs/brief-import-dialog";
import { BriefsOverview } from "@/components/briefs/briefs-overview";
import {
  useBriefConnections,
  useDeleteBriefConnection,
  useSyncBriefConnection,
} from "@/hooks/use-briefs";
import { useDesignConnections } from "@/hooks/use-design-sync";

type Tab = "overview" | "connections";

export default function BriefsPage() {
  const { data: connections, error, isLoading } = useBriefConnections();
  const { trigger: deleteConnection } = useDeleteBriefConnection();
  const { trigger: syncConnection } = useSyncBriefConnection();
  const { mutate } = useSWRConfig();

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      await syncConnection({ id });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/briefs"),
        undefined,
        { revalidate: true },
      );
      toast.success("Briefs synced successfully");
    } catch {
      toast.error("Failed to sync briefs");
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteConnection({ id });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/briefs"),
        undefined,
        { revalidate: true },
      );
      if (selectedId === id) setSelectedId(null);
      toast.success("Connection removed");
    } catch {
      toast.error("Failed to remove connection");
    }
  };

  const { data: designConnections } = useDesignConnections();

  const selectedConnection = connections?.find((c) => c.id === selectedId) ?? null;

  // Resolve design connection for the selected brief connection via shared project_id
  const selectedDesignConnection = (() => {
    if (!selectedConnection?.project_id || !designConnections) return null;
    return designConnections.find((dc) => dc.project_id === selectedConnection.project_id) ?? null;
  })();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="text-foreground-accent h-8 w-8" />
          <div>
            <h1 className="text-foreground text-2xl font-semibold">{"Client Briefs"}</h1>
            <p className="text-foreground-muted text-sm">
              {"Connect your project management tools to import and track campaign briefs"}
            </p>
          </div>
        </div>
        {activeTab === "connections" && (
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          >
            {"Connect Platform"}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-border flex gap-1 border-b" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "overview"}
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "overview"
              ? "border-interactive text-foreground border-b-2"
              : "text-foreground-muted hover:text-foreground"
          }`}
        >
          {"All Briefs"}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "connections"}
          onClick={() => setActiveTab("connections")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "connections"
              ? "border-interactive text-foreground border-b-2"
              : "text-foreground-muted hover:text-foreground"
          }`}
        >
          {"Connections"}
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" ? (
        <BriefsOverview />
      ) : (
        <>
          {/* Error state */}
          {error ? (
            <div className="border-card-border bg-card-bg rounded-lg border px-4 py-12 text-center">
              <p className="text-foreground-muted text-sm">{"Failed to load brief connections"}</p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="text-interactive mt-2 text-sm font-medium hover:underline"
              >
                {"Try again"}
              </button>
            </div>
          ) : !isLoading && connections && connections.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title={"No brief connections"}
              description={
                "Connect a project management tool to import campaign briefs and sync tasks."
              }
              action={
                <button
                  type="button"
                  onClick={() => setDialogOpen(true)}
                  className="text-interactive text-sm font-medium hover:underline"
                >
                  {"Connect Platform"}
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {connections?.map((conn) => (
                <BriefConnectionCard
                  key={conn.id}
                  connection={conn}
                  selected={selectedId === conn.id}
                  syncing={syncingId === conn.id}
                  onSelect={() => setSelectedId(selectedId === conn.id ? null : conn.id)}
                  onSync={() => handleSync(conn.id)}
                  onDelete={() => handleDelete(conn.id)}
                />
              ))}
            </div>
          )}

          {/* Brief Items Panel */}
          {selectedConnection && selectedConnection.status === "connected" && (
            <div className="border-card-border bg-card-bg rounded-lg border p-5">
              <div className="mb-3 flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setImportOpen(true)}
                  className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm font-medium transition-colors"
                >
                  {"Import to Project"}
                </button>
              </div>
              <BriefItemsPanel
                connection={selectedConnection}
                designConnection={selectedDesignConnection}
              />
            </div>
          )}
        </>
      )}

      <ConnectBriefDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      <BriefImportDialog
        connection={selectedConnection}
        open={importOpen}
        onOpenChange={setImportOpen}
      />
    </div>
  );
}
