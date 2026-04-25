"use client";

import { useState } from "react";
import { Trophy, ChevronDown, ChevronUp, Loader2 } from "../icons";
import { useCompetitiveReport, useEmailClients } from "@/hooks/use-ontology";
import type { CapabilityFeasibility } from "@/types/ontology";

function CapabilityRow({ cap }: { cap: CapabilityFeasibility }) {
  const coveragePercent = Math.round(cap.audience_coverage * 100);

  return (
    <div className="border-border bg-card rounded border px-2.5 py-2 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-foreground font-medium">{cap.name}</span>
          <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-[10px] font-medium">
            {cap.category}
          </span>
        </div>
        {cap.hub_supports && cap.hub_agent && (
          <span className="bg-badge-success-bg text-badge-success-text rounded px-1.5 py-0.5 text-[10px] font-medium">
            {`Agent: ${cap.hub_agent}`}
          </span>
        )}
      </div>
      <div className="mt-1.5 flex items-center gap-2">
        <div className="bg-surface-muted h-1.5 flex-1 rounded-full">
          <div
            className="bg-status-success h-1.5 rounded-full"
            style={{ width: `${coveragePercent}%` }}
          />
        </div>
        <span className="text-foreground-muted text-[10px]">
          {`${coveragePercent}% audience coverage`}
        </span>
      </div>
      {cap.blocking_clients.length > 0 && (
        <p className="text-foreground-muted mt-1 text-[10px]">
          {`Blocked by: ${cap.blocking_clients.join(", ")}`}
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
        className="text-foreground-muted flex w-full items-center justify-between text-xs font-medium"
      >
        <span className="flex items-center gap-1.5">
          {title}
          <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${badgeStyle}`}>
            {items.length}
          </span>
        </span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
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
    <div className="bg-surface-muted rounded-lg p-3">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trophy className="text-foreground-muted h-4 w-4" />
          <h3 className="text-foreground-muted text-xs font-medium uppercase tracking-wider">
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
            className="text-foreground-muted hover:text-foreground flex items-center gap-1 text-xs"
          >
            {"Filter by audience…"}
            {selectedClientIds.length > 0 && (
              <span className="bg-primary text-primary-foreground rounded-full px-1.5 py-0.5 text-[10px] font-medium">
                {selectedClientIds.length}
              </span>
            )}
            {filterOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
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
        <div className="text-foreground-muted flex items-center gap-2 text-xs">
          <Loader2 className="h-3 w-3 animate-spin" />
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="space-y-3">
          <p className="text-foreground-muted text-xs">
            {`${report.total_capabilities} capabilities analyzed`}
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
