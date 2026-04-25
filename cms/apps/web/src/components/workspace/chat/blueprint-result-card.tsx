"use client";

import { Zap } from "../../icons";
import { Button } from "@email-hub/ui/components/ui/button";
import type { BlueprintRunResponse } from "@email-hub/sdk";
import {
  PipelineTimeline,
  StatusBanner,
  CollapsibleHandoffs,
  formatDuration,
} from "../blueprint/shared";

interface BlueprintResultCardProps {
  result: BlueprintRunResponse;
  onApplyHtml: (html: string) => void;
}

export function BlueprintResultCard({ result, onApplyHtml }: BlueprintResultCardProps) {
  const totalMs = result.progress?.reduce((sum, n) => sum + n.duration_ms, 0) ?? 0;
  const totalTokens = Object.values(result.model_usage ?? {}).reduce((a, b) => a + b, 0);

  return (
    <div className="border-border bg-card mt-2 space-y-3 rounded-lg border p-3">
      {/* Status banner */}
      <StatusBanner status={result.status} qaPassed={result.qa_passed ?? null} />

      {/* Audience summary if available */}
      {result.audience_summary && (
        <p className="text-muted-foreground text-xs">{result.audience_summary}</p>
      )}

      {/* Pipeline timeline */}
      {result.progress && result.progress.length > 0 && (
        <div>
          <p className="text-muted-foreground mb-2 text-xs font-medium uppercase tracking-wide">
            {"Pipeline"}
          </p>
          <PipelineTimeline progress={result.progress} handoffHistory={result.handoff_history} />
        </div>
      )}

      {/* Handoffs */}
      {result.handoff_history && result.handoff_history.length > 0 && (
        <CollapsibleHandoffs handoffs={result.handoff_history} />
      )}

      {/* Stats row */}
      <div className="text-muted-foreground flex items-center gap-4 text-xs">
        {totalMs > 0 && <span>{formatDuration(totalMs)}</span>}
        {totalTokens > 0 && (
          <span>
            {totalTokens.toLocaleString()} {"tokens"}
          </span>
        )}
        {result.skipped_nodes && result.skipped_nodes.length > 0 && (
          <span>
            {result.skipped_nodes.length} {"skipped"}
          </span>
        )}
      </div>

      {/* Apply button */}
      {result.html && (
        <Button size="sm" className="w-full gap-2" onClick={() => onApplyHtml(result.html)}>
          <Zap className="h-3.5 w-3.5" />
          {"Apply Generated HTML to Editor"}
        </Button>
      )}
    </div>
  );
}
