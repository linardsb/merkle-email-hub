"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ClipboardList } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { EmptyState } from "@/components/ui/empty-state";
import { BriefConnectionCard } from "@/components/briefs/brief-connection-card";
import { BriefItemsPanel } from "@/components/briefs/brief-items-panel";
import { ConnectBriefDialog } from "@/components/briefs/connect-brief-dialog";
import { BriefImportDialog } from "@/components/briefs/brief-import-dialog";
import {
  useBriefConnections,
  useDeleteBriefConnection,
  useSyncBriefConnection,
} from "@/hooks/use-briefs";

export default function BriefsPage() {
  const t = useTranslations("briefs");
  const { data: connections, error, isLoading } = useBriefConnections();
  const { trigger: deleteConnection } = useDeleteBriefConnection();
  const { trigger: syncConnection } = useSyncBriefConnection();
  const { mutate } = useSWRConfig();

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
      toast.success(t("syncSuccess"));
    } catch {
      toast.error(t("syncError"));
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
      toast.success(t("deleteSuccess"));
    } catch {
      toast.error(t("deleteError"));
    }
  };

  const selectedConnection = connections?.find((c) => c.id === selectedId) ?? null;

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <ClipboardList className="h-6 w-6 text-foreground" />
          <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
        </div>
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
          <p className="text-sm text-foreground-muted">{t("error")}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-2 text-sm font-medium text-interactive hover:underline"
          >
            {t("retry")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="h-6 w-6 text-foreground" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {selectedConnection && selectedConnection.status === "connected" && (
            <button
              type="button"
              onClick={() => setImportOpen(true)}
              className="rounded-md border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-surface-hover"
            >
              {t("importTrigger")}
            </button>
          )}
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            {t("connectPlatform")}
          </button>
        </div>
      </div>

      {/* Content */}
      {!isLoading && connections && connections.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title={t("empty")}
          description={t("emptyDescription")}
          action={
            <button
              type="button"
              onClick={() => setDialogOpen(true)}
              className="text-sm font-medium text-interactive hover:underline"
            >
              {t("connectPlatform")}
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
          <BriefItemsPanel connection={selectedConnection} />
        </div>
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
