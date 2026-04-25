"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "../../icons";
import { Badge } from "@email-hub/ui/components/ui/badge";
import type { HandoffSummary } from "@email-hub/sdk";
import { ConfidenceBar } from "./shared";

interface NodeHandoffPanelProps {
  handoff: HandoffSummary;
}

export function NodeHandoffPanel({ handoff }: NodeHandoffPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const hasContent =
    handoff.decisions.length > 0 ||
    handoff.warnings.length > 0 ||
    handoff.component_refs.length > 0;

  if (!hasContent && handoff.confidence == null) return null;

  return (
    <div className="mt-1">
      {handoff.confidence != null && (
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-[10px]">{"Confidence"}</span>
          <ConfidenceBar value={handoff.confidence ?? 0} />
          {(handoff.confidence ?? 0) < 0.5 && (
            <Badge variant="destructive" className="gap-1 px-1.5 py-0 text-[10px]">
              <AlertTriangle className="h-2.5 w-2.5" />
              {"Needs Review"}
            </Badge>
          )}
        </div>
      )}

      {hasContent && (
        <>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-muted-foreground hover:text-foreground mt-0.5 flex items-center gap-1 text-[10px] transition-colors"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {"Agent Decisions"}
          </button>

          {expanded && (
            <div className="border-border bg-muted/30 mt-1 space-y-1.5 rounded border p-2">
              {handoff.decisions.length > 0 && (
                <div>
                  <p className="text-muted-foreground text-[10px] font-medium uppercase tracking-wide">
                    {"Decisions"}
                  </p>
                  <ul className="mt-0.5 space-y-0.5">
                    {handoff.decisions.map((d, i) => (
                      <li key={i} className="text-foreground flex items-start gap-1 text-[10px]">
                        <span className="bg-muted-foreground mt-1 h-1 w-1 shrink-0 rounded-full" />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {handoff.warnings.length > 0 && (
                <div>
                  <p className="text-destructive text-[10px] font-medium uppercase tracking-wide">
                    {"Warnings"}
                  </p>
                  <ul className="mt-0.5 space-y-0.5">
                    {handoff.warnings.map((w, i) => (
                      <li key={i} className="text-destructive flex items-start gap-1 text-[10px]">
                        <AlertTriangle className="mt-0.5 h-2.5 w-2.5 shrink-0" />
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {handoff.component_refs.length > 0 && (
                <div>
                  <p className="text-muted-foreground text-[10px] font-medium uppercase tracking-wide">
                    {"Components Used"}
                  </p>
                  <div className="mt-0.5 flex flex-wrap gap-1">
                    {handoff.component_refs.map((ref) => (
                      <Badge key={ref} variant="secondary" className="px-1 py-0 text-[9px]">
                        {ref}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
