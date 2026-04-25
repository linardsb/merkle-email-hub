"use client";

import { Eye } from "../icons";

/**
 * Placeholder for rendering change timeline.
 * Pending GET /api/v1/ontology/rendering-changes endpoint (21.4+).
 */
export function RenderingChangelog() {
  return (
    <div className="bg-surface-muted rounded-lg p-3">
      <div className="text-foreground-muted flex items-center gap-2">
        <Eye className="h-4 w-4" />
        <span className="text-sm">{"Rendering change detection — coming soon"}</span>
      </div>
    </div>
  );
}
