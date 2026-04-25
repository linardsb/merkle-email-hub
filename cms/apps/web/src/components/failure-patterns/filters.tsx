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
    <div className="border-card-border bg-card-bg flex flex-wrap items-center gap-3 rounded-lg border p-4">
      <Filter className="text-foreground-muted h-4 w-4" />
      <span className="text-foreground-muted text-sm font-medium">{"Filter by"}</span>
      <select
        value={agentFilter}
        onChange={(e) => onAgentChange(e.target.value)}
        className="border-card-border bg-surface text-foreground rounded border px-3 py-1.5 text-sm"
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
        className="border-card-border bg-surface text-foreground rounded border px-3 py-1.5 text-sm"
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
          className="text-interactive text-sm hover:underline"
        >
          {"Clear filters"}
        </button>
      )}
    </div>
  );
}
