"use client";

import { useState } from "react";
import { ClipboardList } from "lucide-react";
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

  const selectedConnection = connections?.find((c) => c.id === selectedId) ?? null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{"Client Briefs"}</h1>
            <p className="text-sm text-foreground-muted">{"Connect your project management tools to import and track campaign briefs"}</p>
          </div>
        </div>
        {activeTab === "connections" && (
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            {"Connect Platform"}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "overview"}
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "overview"
              ? "border-b-2 border-interactive text-foreground"
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
              ? "border-b-2 border-interactive text-foreground"
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
            <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
              <p className="text-sm text-foreground-muted">{"Failed to load brief connections"}</p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-2 text-sm font-medium text-interactive hover:underline"
              >
                {"Try again"}
              </button>
            </div>
          ) : !isLoading && connections && connections.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title={"No brief connections"}
              description={"Connect a project management tool to import campaign briefs and sync tasks."}
              action={
                <button
                  type="button"
                  onClick={() => setDialogOpen(true)}
                  className="text-sm font-medium text-interactive hover:underline"
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
            <div className="rounded-lg border border-card-border bg-card-bg p-5">
              <div className="mb-3 flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setImportOpen(true)}
                  className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
                >
                  {"Import to Project"}
                </button>
              </div>
              <BriefItemsPanel connection={selectedConnection} />
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
