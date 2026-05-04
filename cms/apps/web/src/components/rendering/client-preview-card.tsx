"use client";

import { useState } from "react";
import { Maximize2, Moon, Sun } from "../icons";
import { ConfidenceBar } from "./confidence-bar";
import type { ConfidenceBreakdown } from "@/types/rendering-dashboard";

interface ClientPreviewCardProps {
  clientId: string;
  clientName: string;
  screenshot: string | null; // base64 or null if not yet rendered
  confidence: number;
  breakdown?: ConfidenceBreakdown;
  hasDarkVariant?: boolean;
  darkScreenshot?: string | null;
  onViewFull: (clientId: string) => void;
}

export function ClientPreviewCard({
  clientId,
  clientName,
  screenshot,
  confidence,
  breakdown,
  hasDarkVariant,
  darkScreenshot,
  onViewFull,
}: ClientPreviewCardProps) {
  const [showDark, setShowDark] = useState(false);
  const activeScreenshot = showDark ? darkScreenshot : screenshot;

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-3">
      {/* Screenshot thumbnail */}
      <div className="bg-surface-muted relative mb-2 aspect-[4/3] overflow-hidden rounded-md">
        {activeScreenshot ? (
          <img
            src={`data:image/png;base64,${activeScreenshot}`}
            alt={`${clientName} preview`}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="text-foreground-muted flex h-full items-center justify-center text-xs">
            No preview
          </div>
        )}
        {/* View full button */}
        <button
          type="button"
          onClick={() => onViewFull(clientId)}
          className="bg-surface/80 text-foreground-muted hover:text-foreground absolute top-1.5 right-1.5 rounded p-1"
          title="View full size"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Client name + dark mode toggle */}
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-foreground text-sm font-medium">{clientName}</span>
        {hasDarkVariant && (
          <button
            type="button"
            onClick={() => setShowDark((v) => !v)}
            className="border-card-border text-foreground-muted hover:text-foreground rounded-full border p-1"
            title={showDark ? "Show light mode" : "Show dark mode"}
          >
            {showDark ? <Sun className="h-3 w-3" /> : <Moon className="h-3 w-3" />}
          </button>
        )}
      </div>

      {/* Confidence bar + score */}
      <div className="flex items-center gap-2">
        <ConfidenceBar score={confidence} breakdown={breakdown} size="sm" />
        <span className="text-foreground-muted shrink-0 font-mono text-xs">
          {confidence.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
