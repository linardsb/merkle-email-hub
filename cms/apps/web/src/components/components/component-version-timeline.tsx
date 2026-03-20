"use client";

import { GitCommitVertical, Eye, FlaskConical, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { ComponentPreview } from "./component-preview";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { AppComponentsSchemasVersionResponse as VersionResponse } from "@email-hub/sdk";

interface ComponentVersionTimelineProps {
  componentId: number;
  versions: VersionResponse[];
}

export function ComponentVersionTimeline({
  componentId,
  versions,
}: ComponentVersionTimelineProps) {
  const [previewVersion, setPreviewVersion] = useState<number | null>(null);
  const [runningQAVersion, setRunningQAVersion] = useState<number | null>(null);

  const handleRunQA = async (versionNumber: number) => {
    setRunningQAVersion(versionNumber);
    try {
      await mutationFetcher(
        `/api/v1/components/${componentId}/versions/${versionNumber}/qa`,
        { arg: {} },
      );
      toast.success(`QA completed for v${versionNumber}`);
    } catch {
      toast.error(`QA failed for v${versionNumber}`);
    } finally {
      setRunningQAVersion(null);
    }
  };

  if (versions.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-foreground-muted">
        {"No versions yet"}
      </p>
    );
  }

  const previewHtml = versions.find(
    (v) => v.version_number === previewVersion
  )?.html_source;

  return (
    <div className="space-y-3">
      <ScrollArea className="max-h-80">
        <div className="space-y-0 p-1">
          {versions.map((v, idx) => {
            const isLast = idx === versions.length - 1;
            return (
              <div key={v.id} className="flex gap-3">
                {/* Timeline line + icon */}
                <div className="flex flex-col items-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-muted text-interactive">
                    <GitCommitVertical className="h-4 w-4" />
                  </div>
                  {!isLast && <div className="w-px flex-1 bg-border" />}
                </div>

                {/* Content */}
                <div className={isLast ? "pb-0" : "pb-6"}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">
                      {`v${v.version_number}`}
                    </span>
                    <span className="text-xs text-foreground-muted">
                      {new Date(v.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs text-foreground-muted">
                    {`by User #${v.created_by_id}`}
                  </p>
                  {v.changelog ? (
                    <p className="mt-1 text-xs text-foreground">
                      {v.changelog}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs text-foreground-muted italic">
                      {"No changelog"}
                    </p>
                  )}
                  <div className="mt-1.5 flex gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        setPreviewVersion(
                          previewVersion === v.version_number
                            ? null
                            : v.version_number
                        )
                      }
                      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground"
                    >
                      <Eye className="h-3 w-3" />
                      {"Preview"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRunQA(v.version_number)}
                      disabled={runningQAVersion === v.version_number}
                      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs text-foreground-muted transition-colors hover:bg-surface-hover hover:text-foreground disabled:opacity-50"
                    >
                      {runningQAVersion === v.version_number ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <FlaskConical className="h-3 w-3" />
                      )}
                      {"Run QA"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {previewVersion != null && previewHtml && (
        <div className="overflow-hidden rounded-md border border-border">
          <div className="border-b border-border bg-surface-muted px-3 py-1.5 text-xs font-medium text-foreground-muted">
            {`Preview — v${previewVersion}`}
          </div>
          <ComponentPreview html={previewHtml} height={300} />
        </div>
      )}
    </div>
  );
}
