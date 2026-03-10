"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Bot,
  Cog,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  AlertTriangle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@merkle-email-hub/ui/components/ui/dialog";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import { Badge } from "@merkle-email-hub/ui/components/ui/badge";
import { Label } from "@merkle-email-hub/ui/components/ui/label";
import { useBlueprintRun } from "@/hooks/use-blueprint-run";
import type { BlueprintProgress, HandoffSummary } from "@merkle-email-hub/sdk";

interface BlueprintRunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  currentHtml: string;
  onApplyResult: (html: string) => void;
}

const NODE_LABELS: Record<string, string> = {
  scaffolder: "Scaffolder",
  qa_gate: "QA Gate",
  recovery_router: "Recovery Router",
  dark_mode: "Dark Mode",
  outlook_fixer: "Outlook Fixer",
  accessibility: "Accessibility",
  personalisation: "Personalisation",
  code_reviewer: "Code Reviewer",
  maizzle_build: "Maizzle Build",
  export: "Export",
  knowledge: "Knowledge",
  innovation: "Innovation",
};

function formatNodeName(name: string): string {
  return NODE_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const colorClass =
    value > 0.8
      ? "bg-chart-2"
      : value >= 0.5
        ? "bg-muted-foreground"
        : "bg-destructive";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
}

function PipelineTimeline({ progress }: { progress: BlueprintProgress[] }) {
  const t = useTranslations("blueprintRun");
  return (
    <div className="space-y-1">
      {progress.map((node, idx) => (
        <div key={`${node.node_name}-${node.iteration}-${idx}`} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card">
              {node.node_type === "agentic" ? (
                <Bot className="h-3 w-3 text-foreground" />
              ) : (
                <Cog className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
            {idx < progress.length - 1 && (
              <div className="h-4 w-px bg-border" />
            )}
          </div>
          <div className="flex flex-1 items-center justify-between pb-2">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                  {formatNodeName(node.node_name)}
                </span>
                <Badge
                  variant={node.status === "success" ? "secondary" : node.status === "failed" ? "destructive" : "outline"}
                  className="text-[10px] px-1.5 py-0"
                >
                  {t(`nodeStatus.${node.status}`)}
                </Badge>
                {node.node_type === "agentic" && (
                  <span className="text-[10px] text-muted-foreground">
                    {t(`nodeType.${node.node_type}`)}
                  </span>
                )}
                {node.iteration > 0 && (
                  <span className="text-[10px] text-muted-foreground">
                    {t("iteration", { count: node.iteration + 1 })}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{node.summary}</p>
            </div>
            <div className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDuration(node.duration_ms)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function HandoffSection({ handoffs }: { handoffs: HandoffSummary[] }) {
  const t = useTranslations("blueprintRun");
  return (
    <div className="space-y-3">
      {handoffs.map((handoff, idx) => (
        <div key={`${handoff.agent_name}-${idx}`} className="rounded-lg border border-border bg-card p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {formatNodeName(handoff.agent_name)}
              </Badge>
              {handoff.confidence !== null && (
                <ConfidenceBar value={handoff.confidence} />
              )}
            </div>
          </div>

          {handoff.decisions.length > 0 && (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                {t("handoffDecisions")}
              </p>
              <ul className="mt-1 space-y-0.5">
                {handoff.decisions.map((d, i) => (
                  <li key={i} className="text-xs text-foreground flex items-start gap-1.5">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {handoff.warnings.length > 0 && (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-destructive uppercase tracking-wide">
                {t("handoffWarnings")}
              </p>
              <ul className="mt-1 space-y-0.5">
                {handoff.warnings.map((w, i) => (
                  <li key={i} className="text-xs text-destructive flex items-start gap-1.5">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {handoff.component_refs.length > 0 && (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                {t("handoffComponents")}
              </p>
              <div className="mt-1 flex flex-wrap gap-1">
                {handoff.component_refs.map((ref) => (
                  <Badge key={ref} variant="secondary" className="text-[10px]">
                    {ref}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  completed_with_warnings: "bg-accent text-accent-foreground border-border",
  needs_review: "bg-accent text-accent-foreground border-border",
  cost_cap_exceeded: "bg-destructive/10 text-destructive border-destructive/20",
  running: "bg-muted text-muted-foreground border-border",
};

export function BlueprintRunDialog({
  open,
  onOpenChange,
  projectId,
  currentHtml,
  onApplyResult,
}: BlueprintRunDialogProps) {
  const t = useTranslations("blueprintRun");
  const { run, isRunning, result, error, reset } = useBlueprintRun({ projectId });

  const [brief, setBrief] = useState("");
  const [includeHtml, setIncludeHtml] = useState(false);
  const [showHandoffs, setShowHandoffs] = useState(false);

  const handleRun = useCallback(async () => {
    if (!brief.trim()) return;

    await run({
      blueprint_name: "campaign",
      brief: brief.trim(),
      initial_html: includeHtml ? currentHtml : undefined,
    });
  }, [brief, includeHtml, currentHtml, run]);

  const handleApply = useCallback(() => {
    if (result?.html) {
      onApplyResult(result.html);
      onOpenChange(false);
    }
  }, [result, onApplyResult, onOpenChange]);

  const handleClose = useCallback(() => {
    reset();
    setBrief("");
    setIncludeHtml(false);
    setShowHandoffs(false);
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const totalTokens = result?.model_usage?.total_tokens ?? 0;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[40rem] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            {t("title")}
          </DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        {!result && !isRunning && (
          <div className="space-y-4 py-2">
            {/* Blueprint selector */}
            <div>
              <Label className="text-sm font-medium">{t("blueprintLabel")}</Label>
              <div className="mt-1.5 rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-sm font-medium text-foreground">
                  {t("blueprintTemplates.campaign")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("blueprintTemplates.campaignDescription")}
                </p>
              </div>
            </div>

            {/* Brief input */}
            <div>
              <Label htmlFor="blueprint-brief" className="text-sm font-medium">
                {t("briefLabel")}
              </Label>
              <textarea
                id="blueprint-brief"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder={t("briefPlaceholder")}
                rows={4}
                className="mt-1.5 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Include HTML checkbox */}
            <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={includeHtml}
                onChange={(e) => setIncludeHtml(e.target.checked)}
                className="h-4 w-4 rounded border-border"
              />
              {t("includeHtml")}
            </label>

            {error && (
              <p className="text-sm text-destructive">{t("errors.runFailed")}</p>
            )}
          </div>
        )}

        {isRunning && (
          <div className="flex flex-col items-center justify-center gap-3 py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
            <p className="text-sm text-muted-foreground">{t("running")}</p>
          </div>
        )}

        {result && (
          <div className="space-y-4 py-2">
            {/* Status banner */}
            <div className={`rounded-lg border p-3 ${STATUS_STYLES[result.status] ?? STATUS_STYLES.running}`}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                  {t(`status.${result.status}`)}
                </span>
                <div className="flex items-center gap-3 text-xs">
                  {result.qa_passed === true && (
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {t("qaPassed")}
                    </span>
                  )}
                  {result.qa_passed === false && (
                    <span className="flex items-center gap-1 text-destructive">
                      <XCircle className="h-3.5 w-3.5" />
                      {t("qaFailed")}
                    </span>
                  )}
                  {result.qa_passed === null && (
                    <span className="text-muted-foreground">{t("qaNotReached")}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Audience summary */}
            {result.audience_summary && (
              <div className="rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                  {t("audienceSummary")}
                </p>
                <p className="mt-1 text-xs text-foreground">{result.audience_summary}</p>
              </div>
            )}

            {/* Pipeline timeline */}
            <div>
              <PipelineTimeline progress={result.progress} />
            </div>

            {/* Skipped nodes */}
            {result.skipped_nodes.length > 0 && (
              <div className="rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                  {t("skippedNodes")}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {result.skipped_nodes.map((node) => (
                    <Badge key={node} variant="outline" className="text-xs">
                      {formatNodeName(node)}
                    </Badge>
                  ))}
                </div>
                {result.routing_decisions.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {result.routing_decisions
                      .filter((rd) => rd.action === "skip")
                      .map((rd, i) => (
                        <p key={i} className="text-xs text-muted-foreground">
                          <span className="font-medium">{formatNodeName(rd.node_name)}</span>
                          {" — "}
                          {rd.reason}
                        </p>
                      ))}
                  </div>
                )}
              </div>
            )}

            {/* Handoff history toggle */}
            {result.handoff_history.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowHandoffs((v) => !v)}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showHandoffs ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                  {showHandoffs ? t("hideHandoffs") : t("viewHandoffs")}
                </button>
                {showHandoffs && (
                  <div className="mt-2">
                    <HandoffSection handoffs={result.handoff_history} />
                  </div>
                )}
              </div>
            )}

            {/* Token usage */}
            {totalTokens > 0 && (
              <p className="text-xs text-muted-foreground">
                {t("tokens", { count: totalTokens.toLocaleString() })}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          {!result && !isRunning && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t("cancel")}
              </Button>
              <Button onClick={handleRun} disabled={!brief.trim()}>
                <Zap className="mr-1.5 h-3.5 w-3.5" />
                {t("run")}
              </Button>
            </>
          )}
          {result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {t("close")}
              </Button>
              <Button onClick={handleApply}>
                {t("applyResult")}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
