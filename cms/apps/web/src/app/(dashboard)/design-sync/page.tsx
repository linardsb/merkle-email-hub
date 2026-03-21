"use client";

import { useState, useCallback } from "react";
import { Paintbrush, Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api-error";
import { useSWRConfig } from "swr";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { DesignConnectionCard } from "@/components/design-sync/design-connection-card";
import { DesignTokensView } from "@/components/design-sync/design-tokens-view";
import { ConnectDesignDialog } from "@/components/design-sync/connect-design-dialog";
import { DesignFileBrowser } from "@/components/design-sync/design-file-browser";
import { DesignImportDialog } from "@/components/design-sync/design-import-dialog";
import { authFetch } from "@/lib/auth-fetch";
import {
  useDesignConnections,
  useSyncDesignConnection,
  useRefreshConnectionToken,
} from "@/hooks/use-design-sync";
import type { DesignProvider } from "@/types/design-sync";

type ProviderFilter = "all" | DesignProvider;

const FILTER_TABS: { value: ProviderFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "figma", label: "Figma" },
  { value: "sketch", label: "Sketch" },
  { value: "canva", label: "Canva" },
];

export default function DesignSyncPage() {
  const { data: connections, error, isLoading } = useDesignConnections();
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

  // Refresh token dialog state
  const [refreshTokenDialogOpen, setRefreshTokenDialogOpen] = useState(false);
  const [refreshTokenConnId, setRefreshTokenConnId] = useState<number | null>(null);
  const [refreshTokenValue, setRefreshTokenValue] = useState("");
  const { trigger: refreshToken, isMutating: isRefreshing } = useRefreshConnectionToken(refreshTokenConnId);

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
      toast.success("Design file synced successfully");
    } catch (err) {
      const message = err instanceof Error ? err.message : "";
      const conn = connections?.find((c) => c.id === id);
      const label = conn?.provider ? conn.provider.charAt(0).toUpperCase() + conn.provider.slice(1) : "Design tool";
      const status = err instanceof ApiError ? err.status : 0;
      if (status === 429) {
        toast.error("Too many requests. Please wait a moment and try again.", {
          description: "The server is rate-limiting requests. Wait a few seconds before retrying.",
          duration: 8000,
        });
      } else if (message.includes("access denied")) {
        toast.error(`${label} access denied. Your token may have expired.`, {
          description: "Remove this connection and reconnect with a fresh access token.",
          duration: 8000,
        });
      } else {
        toast.error(`Failed to sync ${label} file`, {
          description: message || undefined,
          duration: 6000,
        });
      }
    } finally {
      setSyncingId(null);
    }
  };

  // Uses authFetch directly to avoid useSWRMutation trigger issues
  const handleDelete = useCallback(async (id: number) => {
    if (!confirm("Remove this connection? This cannot be undone.")) return;
    try {
      const res = await authFetch("/api/v1/design-sync/connections/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      if (!res.ok) throw new Error("Failed to delete");
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
        undefined,
        { revalidate: true },
      );
      if (selectedId === id) setSelectedId(null);
      toast.success("Connection removed");
    } catch {
      toast.error("Failed to remove connection");
    }
  }, [mutate, selectedId]);

  const handleRefreshToken = async () => {
    if (!refreshTokenValue.trim() || !refreshTokenConnId) return;
    try {
      await refreshToken({ access_token: refreshTokenValue.trim() });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/design-sync"),
        undefined,
        { revalidate: true },
      );
      toast.success("Access token refreshed successfully");
      setRefreshTokenDialogOpen(false);
      setRefreshTokenValue("");
      setRefreshTokenConnId(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Check your token and try again.";
      toast.error("Failed to refresh token", { description: message, duration: 6000 });
    }
  };

  const openRefreshTokenDialog = (connId: number) => {
    setRefreshTokenConnId(connId);
    setRefreshTokenValue("");
    setRefreshTokenDialogOpen(true);
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
          <h1 className="text-2xl font-bold text-foreground">{"Design Sync"}</h1>
        </div>
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-12 text-center">
          <p className="text-sm text-foreground-muted">{"Failed to load design connections"}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-2 text-sm font-medium text-interactive hover:underline"
          >
            {"Try again"}
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
            <h1 className="text-2xl font-bold text-foreground">{"Design Sync"}</h1>
            <p className="text-sm text-foreground-muted">{"Connect design files to extract tokens and sync design systems"}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
        >
          {"Connect Design File"}
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
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {!isLoading && filteredConnections && filteredConnections.length === 0 ? (
        <EmptyState
          icon={Paintbrush}
          title={"No design connections"}
          description={"Connect a design file to extract colors, typography, and spacing tokens for your email templates."}
          action={
            <button
              type="button"
              onClick={() => setDialogOpen(true)}
              className="text-sm font-medium text-interactive hover:underline"
            >
              {"Connect Design File"}
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
              onRefreshToken={() => openRefreshTokenDialog(conn.id)}
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
                  {"Import Selected Frames"}
                </button>
              </div>
            )}
          </div>

          {/* Design Tokens */}
          <div className="rounded-lg border border-card-border bg-card-bg p-5">
            <h2 className="mb-4 text-lg font-semibold text-foreground">
              {"Design Tokens"}
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

      {/* Refresh Token Dialog */}
      <Dialog open={refreshTokenDialogOpen} onOpenChange={isRefreshing ? undefined : setRefreshTokenDialogOpen}>
        <DialogContent className="max-w-[28rem]">
          <DialogHeader>
            <DialogTitle>{"Refresh Access Token"}</DialogTitle>
            <DialogDescription>
              {"Enter a new Personal Access Token to restore this connection."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label htmlFor="refresh-token" className="mb-1.5 block text-sm font-medium text-foreground">
                {"New Access Token"}
              </label>
              <input
                id="refresh-token"
                type="password"
                value={refreshTokenValue}
                onChange={(e) => setRefreshTokenValue(e.target.value)}
                placeholder="figd_..."
                disabled={isRefreshing}
                className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50"
              />
              <p className="mt-1 text-xs text-foreground-muted">
                {"Generate a new token from your design tool's developer settings."}
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRefreshTokenDialogOpen(false)}
                disabled={isRefreshing}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
              >
                {"Cancel"}
              </button>
              <button
                type="button"
                onClick={handleRefreshToken}
                disabled={!refreshTokenValue.trim() || isRefreshing}
                className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
              >
                {isRefreshing ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {"Refreshing..."}
                  </span>
                ) : (
                  "Refresh Token"
                )}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
