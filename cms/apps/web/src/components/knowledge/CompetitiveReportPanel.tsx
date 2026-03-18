"use client";

import { useState } from "react";
import {
  Trophy,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { useCompetitiveReport, useEmailClients } from "@/hooks/use-ontology";
import type { CapabilityFeasibility } from "@/types/ontology";

function CapabilityRow({ cap }: { cap: CapabilityFeasibility }) {
  const coveragePercent = Math.round(cap.audience_coverage * 100);

  return (
    <div className="rounded border border-border bg-card px-2.5 py-2 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-foreground">{cap.name}</span>
          <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground-muted">
            {cap.category}
          </span>
        </div>
        {cap.hub_supports && cap.hub_agent && (
          <span className="rounded bg-badge-success-bg px-1.5 py-0.5 text-[10px] font-medium text-badge-success-text">
            {`Agent: \${cap.hub_agent}`}
          </span>
        )}
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-surface-muted">
          <div
            className="h-1.5 rounded-full bg-status-success"
            style={{ width: `${coveragePercent}%` }}
          />
        </div>
        <span className="text-[10px] text-foreground-muted">
          {`\${coveragePercent}% audience coverage`}
        </span>
      </div>
      {cap.blocking_clients.length > 0 && (
        <p className="mt-1 text-[10px] text-foreground-muted">
          {`Blocked by: \${cap.blocking_clients.join("}`}
        </p>
      )}
    </div>
  );
}

function CapabilitySection({
  title,
  items,
  badgeStyle,
}: {
  title: string;
  items: CapabilityFeasibility[];
  badgeStyle: string;
}) {
  const [expanded, setExpanded] = useState(false);

  if (items.length === 0) return null;

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between text-xs font-medium text-foreground-muted"
      >
        <span className="flex items-center gap-1.5">
          {title}
          <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${badgeStyle}`}>
            {items.length}
          </span>
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
      </button>
      {expanded && (
        <div className="mt-1.5 max-h-48 space-y-1 overflow-y-auto">
          {items.map((cap) => (
            <CapabilityRow key={cap.id} cap={cap} />
          ))}
        </div>
      )}
    </div>
  );
}

export function CompetitiveReportPanel() {
  const [selectedClientIds, setSelectedClientIds] = useState<string[]>([]);
  const [filterOpen, setFilterOpen] = useState(false);

  const { data: clients } = useEmailClients();
  const { data: report, isLoading } = useCompetitiveReport(
    selectedClientIds.length > 0 ? selectedClientIds : undefined,
  );

  function toggleClient(id: string) {
    setSelectedClientIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }

  return (
    <div className="rounded-lg bg-surface-muted p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
            {"Competitive Intelligence"}
          </h3>
        </div>
      </div>

      {/* Audience filter */}
      {clients && clients.length > 0 && (
        <div className="mb-2">
          <button
            type="button"
            onClick={() => setFilterOpen((v) => !v)}
            className="flex items-center gap-1 text-xs text-foreground-muted hover:text-foreground"
          >
            {"Filter by audience…"}
            {selectedClientIds.length > 0 && (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-medium text-primary-foreground">
                {selectedClientIds.length}
              </span>
            )}
            {filterOpen ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>
          {filterOpen && (
            <div className="mt-1.5 flex max-h-32 flex-wrap gap-1 overflow-y-auto">
              {clients.map((client) => (
                <button
                  key={client.id}
                  type="button"
                  onClick={() => toggleClient(client.id)}
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                    selectedClientIds.includes(client.id)
                      ? "bg-primary text-primary-foreground"
                      : "bg-card text-foreground-muted hover:bg-surface-hover"
                  }`}
                >
                  {client.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-foreground-muted">
          <Loader2 className="h-3 w-3 animate-spin" />
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="space-y-3">
          <p className="text-xs text-foreground-muted">
            {`\${report.total_capabilities} capabilities analyzed`}
          </p>

          <CapabilitySection
            title={"Hub Advantages"}
            items={report.hub_advantages}
            badgeStyle="bg-badge-success-bg text-badge-success-text"
          />
          <CapabilitySection
            title={"Gaps"}
            items={report.gaps}
            badgeStyle="bg-badge-danger-bg text-badge-danger-text"
          />
          <CapabilitySection
            title={"Opportunities"}
            items={report.opportunities}
            badgeStyle="bg-badge-warning-bg text-badge-warning-text"
          />
        </div>
      )}
    </div>
  );
}
