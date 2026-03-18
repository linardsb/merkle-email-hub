"use client";

import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

const ZOOM_LEVELS = [50, 75, 100, 125] as const;

interface ZoomControlsProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
}

export function ZoomControls({ zoom, onZoomChange }: ZoomControlsProps) {
  const zoomIn = () => {
    const nextLevel = ZOOM_LEVELS.find((l) => l > zoom);
    if (nextLevel) onZoomChange(nextLevel);
  };

  const zoomOut = () => {
    const prevLevel = [...ZOOM_LEVELS].reverse().find((l) => l < zoom);
    if (prevLevel) onZoomChange(prevLevel);
  };

  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <button
        type="button"
        onClick={zoomOut}
        disabled={zoom <= ZOOM_LEVELS[0]}
        className="rounded p-1 hover:bg-muted disabled:opacity-40"
        aria-label="Zoom out"
      >
        <ZoomOut className="h-3.5 w-3.5" />
      </button>
      <span className="min-w-[3ch] text-center">{zoom}%</span>
      <button
        type="button"
        onClick={zoomIn}
        disabled={zoom >= (ZOOM_LEVELS[ZOOM_LEVELS.length - 1] ?? 125)}
        className="rounded p-1 hover:bg-muted disabled:opacity-40"
        aria-label="Zoom in"
      >
        <ZoomIn className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => onZoomChange(100)}
        className="rounded p-1 hover:bg-muted"
        aria-label="Reset zoom"
      >
        <RotateCcw className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
