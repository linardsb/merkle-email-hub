"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock } from "lucide-react";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { useRunCheckpoints } from "@/hooks/use-blueprint-runs";
import { formatNodeName } from "./shared";

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
  const t = useTranslations("blueprintRun");
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading } = useRunCheckpoints(expanded ? runId : null);

  const checkpoints = data?.checkpoints ?? [];

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {t("checkpointsToggle")}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1">
          {isLoading && (
            <div className="flex items-center justify-center py-4">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted border-t-primary" />
            </div>
          )}

          {!isLoading && checkpoints.length === 0 && (
            <p className="text-xs text-muted-foreground">{t("checkpointsEmpty")}</p>
          )}

          {!isLoading && checkpoints.map((cp, idx) => {
            const Icon = CHECKPOINT_STATUS_ICON[cp.status] ?? Clock;
            const colorClass = CHECKPOINT_STATUS_COLOR[cp.status] ?? "text-muted-foreground";
            const isResumePoint = resumedFromNode === cp.node_name;

            return (
              <div key={`${cp.node_name}-${cp.node_index}`} className="flex items-start gap-3">
                <div className="flex flex-col items-center">
                  <div className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                    isResumePoint ? "border-primary bg-primary/10" : "border-border bg-card"
                  }`}>
                    <Icon className={`h-3 w-3 ${isResumePoint ? "text-primary" : colorClass}`} />
                  </div>
                  {idx < checkpoints.length - 1 && <div className="h-3 w-px bg-border" />}
                </div>
                <div className="flex flex-1 items-center justify-between pb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground">
                      {formatNodeName(cp.node_name)}
                    </span>
                    <Badge
                      variant={cp.status === "success" ? "secondary" : cp.status === "failed" ? "destructive" : "outline"}
                      className="text-[10px] px-1.5 py-0"
                    >
                      {t(`nodeStatus.${cp.status}`)}
                    </Badge>
                    {isResumePoint && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-primary text-primary">
                        {t("resumePoint")}
                      </Badge>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground">
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
