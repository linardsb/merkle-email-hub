"use client";

import { useTranslations } from "next-intl";
import { Zap } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Button } from "@email-hub/ui/components/ui/button";
import { Badge } from "@email-hub/ui/components/ui/badge";
import {
  PipelineTimeline,
  StatusBanner,
  CollapsibleHandoffs,
  formatNodeName,
} from "./shared";
import type { BlueprintRunRecord } from "@/types/blueprint-runs";

interface RunDetailDialogProps {
  run: BlueprintRunRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApplyResult?: (html: string) => void;
}

export function RunDetailDialog({
  run,
  open,
  onOpenChange,
  onApplyResult,
}: RunDetailDialogProps) {
  const t = useTranslations("blueprintRuns");
  const tRun = useTranslations("blueprintRun");

  if (!run) return null;

  const runData = run.run_data;
  const formattedDate = new Date(run.created_at).toLocaleString();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[52rem] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            {t("detailTitle")}
          </DialogTitle>
          <DialogDescription>
            {run.brief_excerpt}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{formattedDate}</span>
            <span>·</span>
            <span>{t("durationLabel", { value: (run.duration_ms / 1000).toFixed(1) })}</span>
            <span>·</span>
            <span>{t("tokenCount", { count: run.total_tokens.toLocaleString() })}</span>
          </div>

          {runData ? (
            <>
              <StatusBanner status={runData.status} qaPassed={runData.qa_passed ?? false} />

              {runData.audience_summary && (
                <div className="rounded-lg border border-border bg-muted/50 p-3">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                    {tRun("audienceSummary")}
                  </p>
                  <p className="mt-1 text-xs text-foreground">{runData.audience_summary}</p>
                </div>
              )}

              <PipelineTimeline progress={runData.progress} handoffHistory={runData.handoff_history} />

              {(runData.skipped_nodes ?? []).length > 0 && (
                <div className="rounded-lg border border-border bg-muted/50 p-3">
                  <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                    {tRun("skippedNodes")}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {(runData.skipped_nodes ?? []).map((node) => (
                      <Badge key={node} variant="outline" className="text-xs">
                        {formatNodeName(node)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <CollapsibleHandoffs handoffs={runData.handoff_history ?? []} />
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{t("noRunData")}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tRun("close")}
          </Button>
          {runData?.html && onApplyResult && (
            <Button onClick={() => { onApplyResult(runData.html); onOpenChange(false); }}>
              {tRun("applyResult")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
