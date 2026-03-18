"use client";

import {
  Bot,
  Cog,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { Badge } from "@email-hub/ui/components/ui/badge";
import type { BlueprintProgress, HandoffSummary } from "@email-hub/sdk";
import { useState } from "react";
import { NodeHandoffPanel } from "./node-handoff-panel";

const NODE_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  running: "Running",
  success: "Passed",
  failed: "Failed",
  skipped: "Skipped",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  agentic: "AI Agent",
  deterministic: "System Check",
};

const RUN_STATUS_LABELS: Record<string, string> = {
  running: "Running",
  completed: "Completed",
  completed_with_warnings: "Completed with Warnings",
  cost_cap_exceeded: "Cost Cap Exceeded",
  needs_review: "Needs Review",
  failed: "Failed",
};

export const NODE_LABELS: Record<string, string> = {
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

export function formatNodeName(name: string): string {
  return NODE_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

export const STATUS_STYLES: Record<string, string> = {
  completed: "bg-chart-2/10 text-chart-2 border-chart-2/20",
  completed_with_warnings: "bg-accent text-accent-foreground border-border",
  needs_review: "bg-accent text-accent-foreground border-border",
  cost_cap_exceeded: "bg-destructive/10 text-destructive border-destructive/20",
  failed: "bg-destructive/10 text-destructive border-destructive/20",
  running: "bg-muted text-muted-foreground border-border",
};

export function ConfidenceBar({ value }: { value: number }) {
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

export function PipelineTimeline({ progress, handoffHistory }: { progress: BlueprintProgress[]; handoffHistory?: HandoffSummary[] }) {
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
                  {NODE_STATUS_LABELS[node.status] ?? node.status}
                </Badge>
                {node.node_type === "agentic" && (
                  <span className="text-[10px] text-muted-foreground">
                    {NODE_TYPE_LABELS[node.node_type] ?? node.node_type}
                  </span>
                )}
                {node.iteration > 0 && (
                  <span className="text-[10px] text-muted-foreground">
                    {`Attempt ${node.iteration + 1}`}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">{node.summary}</p>
              {node.node_type === "agentic" && handoffHistory && (() => {
                const handoff = handoffHistory.find((h) => h.agent_name === node.node_name);
                return handoff ? <NodeHandoffPanel handoff={handoff} /> : null;
              })()}
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

export function HandoffSection({ handoffs }: { handoffs: HandoffSummary[] }) {
  return (
    <div className="space-y-3">
      {handoffs.map((handoff, idx) => (
        <div key={`${handoff.agent_name}-${idx}`} className="rounded-lg border border-border bg-card p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {formatNodeName(handoff.agent_name)}
              </Badge>
              {handoff.confidence != null && (
                <ConfidenceBar value={handoff.confidence ?? 0} />
              )}
            </div>
          </div>

          {handoff.decisions.length > 0 && (
            <div className="mt-2">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                {"Decisions"}
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
                {"Warnings"}
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
                {"Components Used"}
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

export function StatusBanner({ status, qaPassed }: { status: string; qaPassed: boolean | null }) {
  return (
    <div className={`rounded-lg border p-3 ${STATUS_STYLES[status] ?? STATUS_STYLES.running}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">
          {RUN_STATUS_LABELS[status] ?? status}
        </span>
        <div className="flex items-center gap-3 text-xs">
          {qaPassed === true && (
            <span className="flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {"QA Gate Passed"}
            </span>
          )}
          {qaPassed === false && (
            <span className="flex items-center gap-1 text-destructive">
              <XCircle className="h-3.5 w-3.5" />
              {"QA Gate Failed"}
            </span>
          )}
          {qaPassed === null && (
            <span className="text-muted-foreground">{"QA Not Reached"}</span>
          )}
        </div>
      </div>
    </div>
  );
}

export function CollapsibleHandoffs({ handoffs }: { handoffs: HandoffSummary[] }) {
  const [show, setShow] = useState(false);

  if (handoffs.length === 0) return null;

  return (
    <div>
      <button
        type="button"
        onClick={() => setShow((v) => !v)}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        {show ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
        {show ? "Hide Agent Decisions" : "View Agent Decisions"}
      </button>
      {show && (
        <div className="mt-2">
          <HandoffSection handoffs={handoffs} />
        </div>
      )}
    </div>
  );
}
