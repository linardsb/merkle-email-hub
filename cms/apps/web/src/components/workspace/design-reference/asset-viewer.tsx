"use client";

import { useState } from "react";
import type { DesignImportAsset } from "@/types/design-sync";

interface AssetViewerProps {
  assets: DesignImportAsset[];
  connectionId: number;
}

export function AssetViewer({ assets, connectionId }: AssetViewerProps) {
  const [selectedIdx, setSelectedIdx] = useState(0);

  if (assets.length === 0) {
    return <p className="text-foreground-muted text-xs">{"No exported assets found"}</p>;
  }

  const selected = assets[selectedIdx] ?? assets[0];
  if (!selected) return null;
  const filename = selected.file_path.split("/").pop() ?? selected.file_path;
  const assetUrl = `/api/v1/design-sync/assets/${connectionId}/${filename}`;

  return (
    <div className="space-y-2">
      {/* Main image */}
      <div className="border-border bg-surface-elevated relative overflow-hidden border">
        <img
          src={assetUrl}
          alt={selected.node_name}
          className="h-auto w-full object-contain"
          style={{ maxHeight: "16rem" }}
        />
      </div>

      {/* Thumbnail strip */}
      {assets.length > 1 && (
        <div className="flex gap-1 overflow-x-auto pb-1">
          {assets.map((asset, idx) => {
            const thumbFilename = asset.file_path.split("/").pop() ?? asset.file_path;
            const thumbUrl = `/api/v1/design-sync/assets/${connectionId}/${thumbFilename}`;
            return (
              <button
                key={asset.id}
                type="button"
                onClick={() => setSelectedIdx(idx)}
                className={`shrink-0 border transition-colors ${
                  idx === selectedIdx
                    ? "border-interactive"
                    : "border-border hover:border-foreground-muted"
                }`}
              >
                <img src={thumbUrl} alt={asset.node_name} className="h-10 w-10 object-cover" />
              </button>
            );
          })}
        </div>
      )}

      {/* Dimensions */}
      {selected.width && selected.height && (
        <p className="text-foreground-muted text-[10px]">
          {selected.node_name} · {selected.width}x{selected.height}
        </p>
      )}
    </div>
  );
}
