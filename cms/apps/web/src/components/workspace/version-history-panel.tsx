"use client";

import { useCallback, useState } from "react";
import { Clock, RotateCcw, Eye, EyeOff, Loader2 } from "../icons";
import { toast } from "sonner";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { useTemplateVersions, useRestoreVersion } from "@/hooks/use-templates";
import type { VersionResponse } from "@/types/templates";

interface VersionHistoryPanelProps {
  templateId: number | null;
  currentVersionNumber: number | null;
  onRestore: (html: string, versionNumber: number) => void;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatFullDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VersionHistoryPanel({
  templateId,
  currentVersionNumber,
  onRestore,
}: VersionHistoryPanelProps) {
  const { data: versions, isLoading, mutate: mutateVersions } = useTemplateVersions(templateId);
  const { trigger: restoreVersion, isMutating: isRestoring } = useRestoreVersion(templateId);
  const [previewVersionId, setPreviewVersionId] = useState<number | null>(null);
  const [restoringVersion, setRestoringVersion] = useState<number | null>(null);

  const handleRestore = useCallback(
    async (version: VersionResponse) => {
      if (isRestoring || version.version_number === currentVersionNumber) return;

      setRestoringVersion(version.version_number);
      try {
        const result = await restoreVersion({ version_number: version.version_number });
        if (result) {
          onRestore(result.html_source, result.version_number);
          await mutateVersions();
          toast.success(
            `Restored to version ${version.version_number} (saved as v${result.version_number})`,
          );
        }
      } catch {
        toast.error("Failed to restore version");
      } finally {
        setRestoringVersion(null);
      }
    },
    [isRestoring, currentVersionNumber, restoreVersion, onRestore, mutateVersions],
  );

  const togglePreview = useCallback((versionId: number) => {
    setPreviewVersionId((prev) => (prev === versionId ? null : versionId));
  }, []);

  if (!templateId) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground text-xs">No template selected</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center gap-2">
        <Loader2 className="text-muted-foreground h-4 w-4 animate-spin" />
        <p className="text-muted-foreground text-xs">Loading history...</p>
      </div>
    );
  }

  if (!versions?.length) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground text-xs">
          No versions yet — save to create your first version
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-0.5 p-2">
        {versions.map((version) => {
          const isCurrent = version.version_number === currentVersionNumber;
          const isBeingRestored = restoringVersion === version.version_number;
          const isPreviewing = previewVersionId === version.id;

          return (
            <div key={version.id}>
              <div
                className={`group flex items-center gap-3 rounded-md px-3 py-2 text-xs transition-colors ${
                  isCurrent
                    ? "bg-primary/10 border-primary/20 border"
                    : "hover:bg-muted/50 border border-transparent"
                }`}
              >
                {/* Version indicator */}
                <div className="text-muted-foreground flex shrink-0 items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="font-mono font-medium">v{version.version_number}</span>
                </div>

                {/* Timestamp and changelog */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="text-muted-foreground"
                      title={formatFullDate(version.created_at)}
                    >
                      {formatRelativeTime(version.created_at)}
                    </span>
                    {isCurrent && (
                      <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
                        current
                      </Badge>
                    )}
                  </div>
                  {version.changelog && (
                    <p className="text-muted-foreground/70 mt-0.5 truncate">{version.changelog}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={() => togglePreview(version.id)}
                    className="text-muted-foreground hover:bg-accent hover:text-foreground rounded p-1 transition-colors"
                    title={isPreviewing ? "Hide preview" : "Preview HTML"}
                  >
                    {isPreviewing ? (
                      <EyeOff className="h-3.5 w-3.5" />
                    ) : (
                      <Eye className="h-3.5 w-3.5" />
                    )}
                  </button>
                  {!isCurrent && (
                    <button
                      type="button"
                      onClick={() => handleRestore(version)}
                      disabled={isRestoring}
                      className="text-muted-foreground hover:bg-accent hover:text-foreground rounded p-1 transition-colors disabled:opacity-50"
                      title="Restore this version"
                    >
                      {isBeingRestored ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="h-3.5 w-3.5" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Inline HTML preview */}
              {isPreviewing && (
                <div className="border-border bg-muted/30 mx-3 mt-1 mb-1 overflow-hidden rounded border">
                  <pre className="text-muted-foreground max-h-48 overflow-auto p-2 text-[10px] leading-relaxed">
                    <code>
                      {version.html_source.length > 3000
                        ? `${version.html_source.slice(0, 3000)}…`
                        : version.html_source}
                    </code>
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
