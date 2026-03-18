"use client";

import { useEffect, useRef, useCallback } from "react";
import { Eye, EyeOff } from "lucide-react";
import type { ChangedRegion } from "@/types/rendering";

interface DiffOverlayProps {
  originalBase64: string;
  diffBase64: string | null;
  diffPercentage: number;
  changedRegions: ChangedRegion[];
  showDiff: boolean;
  onToggleDiff: () => void;
}

function getDiffBadge(
  percentage: number,
): { label: string; className: string } {
  if (percentage < 1) {
    return {
      label: "Identical",
      className: "bg-badge-success-bg text-badge-success-text",
    };
  }
  if (percentage <= 5) {
    return {
      label: "Minor Changes",
      className: "bg-badge-warning-bg text-badge-warning-text",
    };
  }
  return {
    label: "Major Changes",
    className: "bg-badge-danger-bg text-badge-danger-text",
  };
}

export function DiffOverlay({
  originalBase64,
  diffBase64,
  diffPercentage,
  changedRegions,
  showDiff,
  onToggleDiff,
}: DiffOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const badge = getDiffBadge(diffPercentage);

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function drawRegions(c: CanvasRenderingContext2D) {
      if (!showDiff) return;
      c.strokeStyle = "#ef4444"; // red for changed regions
      c.lineWidth = 2;
      for (const region of changedRegions) {
        c.strokeRect(region.x, region.y, region.width, region.height);
      }
    }

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);

      // Overlay diff image if toggled on
      if (showDiff && diffBase64) {
        const diffImg = new Image();
        diffImg.onload = () => {
          ctx.globalAlpha = 0.5;
          ctx.drawImage(diffImg, 0, 0);
          ctx.globalAlpha = 1.0;
          drawRegions(ctx);
        };
        diffImg.src = `data:image/png;base64,${diffBase64}`;
      } else {
        drawRegions(ctx);
      }
    };
    img.src = `data:image/png;base64,${originalBase64}`;
  }, [originalBase64, diffBase64, showDiff, changedRegions]);

  useEffect(() => {
    drawCanvas();
  }, [drawCanvas]);

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onToggleDiff}
          disabled={!diffBase64}
          className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
        >
          {showDiff ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
          {showDiff ? "Hide Diff Overlay" : "Show Diff Overlay"}
        </button>

        <div className="flex items-center gap-2">
          <span className="text-sm text-foreground-muted">
            {`Diff: \${diffPercentage.toFixed(2)}%`}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}
          >
            {badge.label}
          </span>
        </div>
      </div>

      {/* Canvas */}
      <div className="overflow-hidden rounded-lg border border-border bg-surface-muted">
        <canvas
          ref={canvasRef}
          className="h-auto max-h-[32rem] w-full object-contain"
        />
      </div>
    </div>
  );
}
