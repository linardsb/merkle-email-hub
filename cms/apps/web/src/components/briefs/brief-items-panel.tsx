"use client";

import { useState } from "react";
import { Loader2 } from "../icons";
import { useBriefItems } from "@/hooks/use-briefs";
import { BriefItemCard } from "./brief-item-card";
import { BriefDetailDialog } from "./brief-detail-dialog";
import { DesignImportDialog } from "@/components/design-sync/design-import-dialog";
import { ConnectDesignDialog } from "@/components/design-sync/connect-design-dialog";
import type { BriefConnection } from "@/types/briefs";
import type { DesignConnection } from "@/types/design-sync";

interface BriefItemsPanelProps {
  connection: BriefConnection;
  designConnection?: DesignConnection | null;
}

export function BriefItemsPanel({ connection, designConnection }: BriefItemsPanelProps) {
  const { data: items, isLoading, error } = useBriefItems(connection.id);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [syncConnection, setSyncConnection] = useState<DesignConnection | null>(null);
  const [showConnectDialog, setShowConnectDialog] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="text-foreground-muted h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-foreground-muted py-4 text-center text-sm">
        {"Failed to load brief items"}
      </p>
    );
  }

  if (!items || items.length === 0) {
    return <p className="text-foreground-muted py-4 text-center text-sm">{"No brief items"}</p>;
  }

  return (
    <>
      <div className="space-y-2">
        <h3 className="text-foreground text-sm font-medium">{`Briefs from ${connection.name}`}</h3>
        {items.map((item) => (
          <BriefItemCard key={item.id} item={item} onSelect={() => setSelectedItemId(item.id)} />
        ))}
      </div>

      <BriefDetailDialog
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedItemId(null);
        }}
        designConnection={designConnection}
        onSyncDesign={(connId) => {
          setSelectedItemId(null);
          if (designConnection && designConnection.id === connId) {
            setSyncConnection(designConnection);
          }
        }}
        onConnectDesign={() => {
          setSelectedItemId(null);
          setShowConnectDialog(true);
        }}
      />

      {syncConnection && (
        <DesignImportDialog
          open
          onOpenChange={(open) => {
            if (!open) setSyncConnection(null);
          }}
          connectionId={syncConnection.id}
          connectionName={syncConnection.name}
          initialTab="components"
        />
      )}
      <ConnectDesignDialog open={showConnectDialog} onOpenChange={setShowConnectDialog} />
    </>
  );
}
