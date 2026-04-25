"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock } from "../../icons";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { useRunCheckpoints } from "@/hooks/use-blueprint-runs";
import { formatNodeName } from "./shared";

const NODE_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  running: "Running",
  success: "Passed",
  failed: "Failed",
  skipped: "Skipped",
};

const CHECKPOINT_STATUS_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle2,
  failed: XCircle,
  unknown: Clock,
};

const CHECKPOINT_STATUS_COLOR: Record<string, string> = {
  success: "text-chart-2",
  failed: "text-destructive",
  unknown: "text-muted-foreground",
};

interface RunCheckpointsProps {
  runId: string;
  resumedFromNode?: string | null;
}

export function RunCheckpoints({ runId, resumedFromNode }: RunCheckpointsProps) {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading } = useRunCheckpoints(expanded ? runId : null);

  const checkpoints = data?.checkpoints ?? [];

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="text-muted-foreground hover:text-foreground flex items-center gap-1.5 text-sm transition-colors"
      >
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {"Checkpoints"}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1">
          {isLoading && (
            <div className="flex items-center justify-center py-4">
              <div className="border-muted border-t-primary h-4 w-4 animate-spin rounded-full border-2" />
            </div>
          )}

          {!isLoading && checkpoints.length === 0 && (
            <p className="text-muted-foreground text-xs">{"No checkpoints available"}</p>
          )}

          {!isLoading &&
            checkpoints.map((cp, idx) => {
              const Icon = CHECKPOINT_STATUS_ICON[cp.status] ?? Clock;
              const colorClass = CHECKPOINT_STATUS_COLOR[cp.status] ?? "text-muted-foreground";
              const isResumePoint = resumedFromNode === cp.node_name;

              return (
                <div key={`${cp.node_name}-${cp.node_index}`} className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                        isResumePoint ? "border-primary bg-primary/10" : "border-border bg-card"
                      }`}
                    >
                      <Icon className={`h-3 w-3 ${isResumePoint ? "text-primary" : colorClass}`} />
                    </div>
                    {idx < checkpoints.length - 1 && <div className="bg-border h-3 w-px" />}
                  </div>
                  <div className="flex flex-1 items-center justify-between pb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-foreground text-xs font-medium">
                        {formatNodeName(cp.node_name)}
                      </span>
                      <Badge
                        variant={
                          cp.status === "success"
                            ? "secondary"
                            : cp.status === "failed"
                              ? "destructive"
                              : "outline"
                        }
                        className="px-1.5 py-0 text-[10px]"
                      >
                        {NODE_STATUS_LABELS[cp.status] ?? cp.status}
                      </Badge>
                      {isResumePoint && (
                        <Badge
                          variant="outline"
                          className="border-primary text-primary px-1.5 py-0 text-[10px]"
                        >
                          {"Resume Point"}
                        </Badge>
                      )}
                    </div>
                    <span className="text-muted-foreground text-[10px]">
                      {new Date(cp.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
