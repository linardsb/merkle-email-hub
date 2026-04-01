"use client";

import { Filter } from "../icons";

interface FailurePatternFiltersProps {
  agents: string[];
  checks: string[];
  agentFilter: string;
  checkFilter: string;
  onAgentChange: (value: string) => void;
  onCheckChange: (value: string) => void;
}

export function FailurePatternFilters({
  agents,
  checks,
  agentFilter,
  checkFilter,
  onAgentChange,
  onCheckChange,
}: FailurePatternFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-card-border bg-card-bg p-4">
      <Filter className="h-4 w-4 text-foreground-muted" />
      <span className="text-sm font-medium text-foreground-muted">
        {"Filter by"}
      </span>
      <select
        value={agentFilter}
        onChange={(e) => onAgentChange(e.target.value)}
        className="rounded border border-card-border bg-surface px-3 py-1.5 text-sm text-foreground"
      >
        <option value="">{"All agents"}</option>
        {agents.map((agent) => (
          <option key={agent} value={agent}>
            {agent.replace(/_/g, " ")}
          </option>
        ))}
      </select>
      <select
        value={checkFilter}
        onChange={(e) => onCheckChange(e.target.value)}
        className="rounded border border-card-border bg-surface px-3 py-1.5 text-sm text-foreground"
      >
        <option value="">{"All checks"}</option>
        {checks.map((check) => (
          <option key={check} value={check}>
            {check.replace(/_/g, " ")}
          </option>
        ))}
      </select>
      {(agentFilter || checkFilter) && (
        <button
          onClick={() => {
            onAgentChange("");
            onCheckChange("");
          }}
          className="text-sm text-interactive hover:underline"
        >
          {"Clear filters"}
        </button>
      )}
    </div>
  );
}
