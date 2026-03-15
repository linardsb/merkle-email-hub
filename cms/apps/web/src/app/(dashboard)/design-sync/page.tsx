"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Paintbrush, Download } from "lucide-react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { EmptyState } from "@/components/ui/empty-state";
import { DesignConnectionCard } from "@/components/design-sync/design-connection-card";
import { DesignTokensView } from "@/components/design-sync/design-tokens-view";
import { ConnectDesignDialog } from "@/components/design-sync/connect-design-dialog";
import { DesignFileBrowser } from "@/components/design-sync/design-file-browser";
import { DesignImportDialog } from "@/components/design-sync/design-import-dialog";
import {
  useDesignConnections,
  useDeleteDesignConnection,
  useSyncDesignConnection,
} from "@/hooks/use-design-sync";
import type { DesignProvider } from "@/types/design-sync";

type ProviderFilter = "all" | DesignProvider;

const FILTER_TABS: { value: ProviderFilter; labelKey: string }[] = [
  { value: "all", labelKey: "filterAll" },
  { value: "figma", labelKey: "providerFigma" },
  { value: "sketch", labelKey: "providerSketch" },
  { value: "canva", labelKey: "providerCanva" },
];

export default function DesignSyncPage() {
  const t = useTranslations("designSync");
  const { data: connections, error, isLoading } = useDesignConnections();
  const { trigger: deleteConnection } = useDeleteDesignConnection();
  const { trigger: syncConnection } = useSyncDesignConnection();
  const { mutate } = useSWRConfig();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>("all");

  // Import dialog state
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importConnectionId, setImportConnectionId] = useState<number | null>(null);
  const [importConnectionName, setImportConnectionName] = useState("");
  const [importInitialTab, setImportInitialTab] = useState<"import" | "components">("import");

  // File browser selection state
  const [browserNodeIds, setBrowserNodeIds] = useState<string[]>([]);

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      await syncConnection({ id });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
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
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
        undefined,
        { revalidate: true },
      );
      if (selectedId === id) setSelectedId(null);
      toast.success(t("deleteSuccess"));
    } catch {
      toast.error(t("deleteError"));
    }
  };

  const openImportDialog = (connId: number, connName: string, tab: "import" | "components") => {
    setImportConnectionId(connId);
    setImportConnectionName(connName);
    setImportInitialTab(tab);
    setBrowserNodeIds([]);
    setImportDialogOpen(true);
  };

  const openImportWithSelection = (connId: number, connName: string) => {
    setImportConnectionId(connId);
    setImportConnectionName(connName);
    setImportInitialTab("import");
    setImportDialogOpen(true);
    // browserNodeIds already set from file browser
  };

  const filteredConnections = connections?.filter(
    (c) => providerFilter === "all" || c.provider === providerFilter,
  );

  const selectedConnection = connections?.find((c) => c.id === selectedId);
  const showTokens = selectedConnection?.status === "connected";

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Paintbrush className="h-6 w-6 text-foreground" />
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
          <Paintbrush className="h-6 w-6 text-foreground" />
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

      {/* Provider filter tabs */}
      <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setProviderFilter(tab.value)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              providerFilter === tab.value
                ? "bg-interactive text-foreground-inverse"
                : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
            }`}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {/* Content */}
      {!isLoading && filteredConnections && filteredConnections.length === 0 ? (
        <EmptyState
          icon={Paintbrush}
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
          {filteredConnections?.map((conn) => (
            <DesignConnectionCard
              key={conn.id}
              connection={conn}
              selected={selectedId === conn.id}
              syncing={syncingId === conn.id}
              onSelect={() => setSelectedId(selectedId === conn.id ? null : conn.id)}
              onSync={() => handleSync(conn.id)}
              onDelete={() => handleDelete(conn.id)}
              onImport={() => openImportDialog(conn.id, conn.name, "import")}
              onExtractComponents={() => openImportDialog(conn.id, conn.name, "components")}
            />
          ))}
        </div>
      )}

      {/* Expanded panels for selected connection */}
      {showTokens && selectedId !== null && selectedConnection && (
        <div className="space-y-6">
          {/* File Browser */}
          <div className="rounded-lg border border-card-border bg-card-bg p-5">
            <DesignFileBrowser
              connectionId={selectedId}
              selectedNodeIds={browserNodeIds}
              onSelectionChange={setBrowserNodeIds}
            />
            {browserNodeIds.length > 0 && (
              <div className="mt-3 flex justify-end border-t border-card-border pt-3">
                <button
                  type="button"
                  onClick={() => openImportWithSelection(selectedId, selectedConnection.name)}
                  className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
                >
                  <Download className="h-4 w-4" />
                  {t("importSelected")}
                </button>
              </div>
            )}
          </div>

          {/* Design Tokens */}
          <div className="rounded-lg border border-card-border bg-card-bg p-5">
            <h2 className="mb-4 text-lg font-semibold text-foreground">
              {t("tokensTitle")}
            </h2>
            <DesignTokensView connectionId={selectedId} />
          </div>
        </div>
      )}

      <ConnectDesignDialog open={dialogOpen} onOpenChange={setDialogOpen} />

      {importConnectionId !== null && (
        <DesignImportDialog
          open={importDialogOpen}
          onOpenChange={setImportDialogOpen}
          connectionId={importConnectionId}
          connectionName={importConnectionName}
          initialNodeIds={browserNodeIds}
          initialTab={importInitialTab}
        />
      )}
    </div>
  );
}
