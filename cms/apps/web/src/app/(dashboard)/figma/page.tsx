"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Figma } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { EmptyState } from "@/components/ui/empty-state";
import { FigmaConnectionCard } from "@/components/figma/figma-connection-card";
import { FigmaDesignTokensView } from "@/components/figma/figma-design-tokens";
import { ConnectFigmaDialog } from "@/components/figma/connect-figma-dialog";
import {
  useFigmaConnections,
  useDeleteFigmaConnection,
  useSyncFigmaConnection,
} from "@/hooks/use-figma";

export default function FigmaPage() {
  const t = useTranslations("figma");
  const { data: connections, error, isLoading } = useFigmaConnections();
  const { trigger: deleteConnection } = useDeleteFigmaConnection();
  const { trigger: syncConnection } = useSyncFigmaConnection();
  const { mutate } = useSWRConfig();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      await syncConnection({ id });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/figma"),
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
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/figma"),
        undefined,
        { revalidate: true },
      );
      if (selectedId === id) setSelectedId(null);
      toast.success(t("deleteSuccess"));
    } catch {
      toast.error(t("deleteError"));
    }
  };

  const selectedConnection = connections?.find((c) => c.id === selectedId);
  const showTokens = selectedConnection?.status === "connected";

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Figma className="h-6 w-6 text-foreground" />
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
          <Figma className="h-6 w-6 text-foreground" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
        >
          {t("connectFile")}
        </button>
      </div>

      {/* Content */}
      {!isLoading && connections && connections.length === 0 ? (
        <EmptyState
          icon={Figma}
          title={t("empty")}
          description={t("emptyDescription")}
          action={
            <button
              type="button"
              onClick={() => setDialogOpen(true)}
              className="text-sm font-medium text-interactive hover:underline"
            >
              {t("connectFile")}
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {connections?.map((conn) => (
            <FigmaConnectionCard
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

      {/* Design Tokens Preview */}
      {showTokens && selectedId !== null && (
        <div className="rounded-lg border border-card-border bg-card-bg p-5">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            {t("tokensTitle")}
          </h2>
          <FigmaDesignTokensView connectionId={selectedId} />
        </div>
      )}

      <ConnectFigmaDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}
