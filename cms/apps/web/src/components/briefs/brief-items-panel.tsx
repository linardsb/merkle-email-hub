"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useBriefItems } from "@/hooks/use-briefs";
import { BriefItemCard } from "./brief-item-card";
import { BriefDetailDialog } from "./brief-detail-dialog";
import type { BriefConnection } from "@/types/briefs";

interface BriefItemsPanelProps {
  connection: BriefConnection;
}

export function BriefItemsPanel({ connection }: BriefItemsPanelProps) {
  const { data: items, isLoading, error } = useBriefItems(connection.id);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="py-4 text-center text-sm text-foreground-muted">{"Failed to load brief items"}</p>
    );
  }

  if (!items || items.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-foreground-muted">{"No brief items"}</p>
    );
  }

  return (
    <>
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-foreground">
          {`Briefs from \${connection.name}`}
        </h3>
        {items.map((item) => (
          <BriefItemCard
            key={item.id}
            item={item}
            onSelect={() => setSelectedItemId(item.id)}
          />
        ))}
      </div>

      <BriefDetailDialog
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedItemId(null);
        }}
      />
    </>
  );
}
