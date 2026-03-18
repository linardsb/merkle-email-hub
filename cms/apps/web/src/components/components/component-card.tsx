"use client";

import { useComponentVersions } from "@/hooks/use-components";
import { ComponentPreview } from "./component-preview";
import { CompatibilityBadge } from "./compatibility-badge";
import type { ComponentResponse } from "@email-hub/sdk";

interface ComponentCardProps {
  component: ComponentResponse;
  onClick: () => void;
}

export function ComponentCard({ component, onClick }: ComponentCardProps) {
  const { data: versions } = useComponentVersions(component.id);
  const latestHtml = versions?.[0]?.html_source ?? null;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="cursor-pointer overflow-hidden rounded-lg border border-card-border bg-card-bg transition-colors hover:border-interactive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-interactive"
    >
      <ComponentPreview html={latestHtml} height={200} />

      <div className="border-t border-card-border p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-medium text-foreground">
              {component.name}
            </h3>
            {component.description && (
              <p className="mt-0.5 truncate text-xs text-foreground-muted">
                {component.description}
              </p>
            )}
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          {component.category && (
            <span className="rounded-full bg-badge-default-bg px-2 py-0.5 text-xs font-medium text-badge-default-text">
              {component.category}
            </span>
          )}
          <CompatibilityBadge badge={component.compatibility_badge} />
          <span className="text-xs text-foreground-muted">
            {component.latest_version
              ? `v${component.latest_version}`
              : "No versions"}
          </span>
        </div>
      </div>
    </div>
  );
}
