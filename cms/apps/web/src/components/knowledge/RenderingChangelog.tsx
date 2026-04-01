"use client";

import { Eye } from "../icons";

/**
 * Placeholder for rendering change timeline.
 * Pending GET /api/v1/ontology/rendering-changes endpoint (21.4+).
 */
export function RenderingChangelog() {
  return (
    <div className="rounded-lg bg-surface-muted p-3">
      <div className="flex items-center gap-2 text-foreground-muted">
        <Eye className="h-4 w-4" />
        <span className="text-sm">{"Rendering change detection — coming soon"}</span>
      </div>
    </div>
  );
}
