"use client";

import { useState } from "react";
import { Paintbrush, ExternalLink, FolderOpen } from "../icons";
import { usePenpotConnections } from "@/hooks/use-penpot";
import { DesignFileBrowser } from "@/components/design-sync/design-file-browser";
import Link from "next/link";

export function PenpotPanel() {
  const { data: connections, isLoading } = usePenpotConnections();
  const [browsingConnectionId, setBrowsingConnectionId] = useState<number | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="border-card-border bg-card-bg h-24 animate-pulse rounded-lg border"
          />
        ))}
      </div>
    );
  }

  if (!connections || connections.length === 0) {
    return (
      <div className="border-card-border bg-card-bg flex flex-col items-center gap-4 rounded-lg border py-16">
        <Paintbrush className="text-foreground-muted h-12 w-12" />
        <div className="text-center">
          <p className="font-medium">No Penpot connections</p>
          <p className="text-foreground-muted mt-1 text-sm">
            Connect your first Penpot project from the Design Sync page.
          </p>
        </div>
        <Link
          href="/design-sync"
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-4 py-2 text-sm font-medium"
        >
          Go to Design Sync
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Quick Actions */}
      <div className="flex items-center justify-between">
        <p className="text-foreground-muted text-sm">
          {connections.length} Penpot connection{connections.length !== 1 ? "s" : ""}
        </p>
        <Link
          href="/design-sync"
          className="text-interactive flex items-center gap-1.5 text-sm hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" /> Connect New Project
        </Link>
      </div>

      {/* Connection Cards */}
      {connections.map((conn) => (
        <div key={conn.id} className="border-card-border bg-card-bg rounded-lg border p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block h-2.5 w-2.5 rounded-full ${
                    conn.status === "connected" ? "bg-status-success" : "bg-foreground-muted"
                  }`}
                />
                <span className="font-medium">{conn.name}</span>
              </div>
              <div className="text-foreground-muted mt-1 flex gap-3 text-sm">
                <span>Status: {conn.status}</span>
                {conn.last_synced_at && (
                  <span>Last synced: {new Date(conn.last_synced_at).toLocaleDateString()}</span>
                )}
                {conn.project_name && <span>Project: {conn.project_name}</span>}
              </div>
            </div>
            <button
              onClick={() => {
                if (browsingConnectionId === conn.id) {
                  setBrowsingConnectionId(null);
                } else {
                  setBrowsingConnectionId(conn.id);
                  setSelectedNodeIds([]);
                }
              }}
              className="border-card-border text-foreground-muted hover:bg-surface-hover flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm"
            >
              <FolderOpen className="h-4 w-4" />
              {browsingConnectionId === conn.id ? "Close" : "Browse Files"}
            </button>
          </div>

          {browsingConnectionId === conn.id && (
            <div className="border-card-border mt-4 border-t pt-4">
              <DesignFileBrowser
                connectionId={conn.id}
                selectedNodeIds={selectedNodeIds}
                onSelectionChange={setSelectedNodeIds}
              />
              {selectedNodeIds.length > 0 && (
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-foreground-muted text-sm">
                    {selectedNodeIds.length} node{selectedNodeIds.length !== 1 ? "s" : ""} selected
                  </p>
                  <Link
                    href="/design-sync"
                    className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium"
                  >
                    Import in Design Sync
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
