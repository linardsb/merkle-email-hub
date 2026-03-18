"use client";

import { Puzzle, GitBranch, FileText, Paintbrush } from "lucide-react";
import { usePluginHealthSummary } from "@/hooks/use-plugins";
import { useWorkflows } from "@/hooks/use-workflows";
import { usePenpotConnections } from "@/hooks/use-penpot";
import type { EcosystemTab } from "@/types/ecosystem";

interface Props {
  onNavigate: (tab: EcosystemTab) => void;
}

const STATUS_DOT: Record<string, string> = {
  healthy: "bg-status-success",
  active: "bg-status-success",
  connected: "bg-status-success",
  degraded: "bg-status-warning",
  error: "bg-status-error",
  unhealthy: "bg-status-error",
  disabled: "bg-foreground-muted",
};

export function EcosystemDashboard({ onNavigate }: Props) {
  const { data: health, isLoading: healthLoading } = usePluginHealthSummary();
  const { data: workflows, isLoading: workflowsLoading } = useWorkflows();
  const { data: penpotConns, isLoading: penpotLoading } = usePenpotConnections();

  const cards = [
    {
      label: "Plugins",
      value: health ? `${health.healthy}/${health.total} healthy` : "—",
      icon: Puzzle,
      colorClass: health?.degraded || health?.unhealthy ? "text-status-warning" : "text-status-success",
    },
    {
      label: "Workflows",
      value: workflows ? `${workflows.flows.length} flows` : "—",
      icon: GitBranch,
      colorClass: "text-foreground",
    },
    {
      label: "Reports",
      value: "On-demand",
      icon: FileText,
      colorClass: "text-foreground-muted",
    },
    {
      label: "Penpot",
      value: penpotConns ? `${penpotConns.length} connections` : "—",
      icon: Paintbrush,
      colorClass: penpotConns && penpotConns.length > 0 ? "text-status-success" : "text-foreground-muted",
    },
  ];

  const isAnyLoading = healthLoading || workflowsLoading || penpotLoading;

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-card-border bg-card-bg p-4"
          >
            {isAnyLoading ? (
              <div className="space-y-2">
                <div className="h-4 w-20 animate-pulse rounded bg-surface-hover" />
                <div className="h-6 w-24 animate-pulse rounded bg-surface-hover" />
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-sm text-foreground-muted">
                  <card.icon className="h-4 w-4" />
                  {card.label}
                </div>
                <p className={`mt-1 text-lg font-semibold ${card.colorClass}`}>
                  {card.value}
                </p>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Quadrant Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Plugins Quadrant */}
        <QuadrantCard
          title="Plugins"
          icon={<Puzzle className="h-5 w-5" />}
          onViewAll={() => onNavigate("plugins")}
          isLoading={healthLoading}
        >
          {health && (
            <div className="space-y-3">
              <div className="flex gap-3 text-sm">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-status-success" />
                  {health.healthy} healthy
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-status-warning" />
                  {health.degraded} degraded
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-status-error" />
                  {health.unhealthy} unhealthy
                </span>
              </div>
              <ul className="space-y-2">
                {health.plugins.slice(0, 3).map((p) => (
                  <li key={p.name} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2">
                      <span className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[p.status] ?? "bg-foreground-muted"}`} />
                      {p.name}
                    </span>
                    <span className="text-foreground-muted">{p.latency_ms}ms</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </QuadrantCard>

        {/* Workflows Quadrant */}
        <QuadrantCard
          title="Workflows"
          icon={<GitBranch className="h-5 w-5" />}
          onViewAll={() => onNavigate("workflows")}
          isLoading={workflowsLoading}
        >
          {workflows && (
            <div className="space-y-3">
              <p className="text-sm text-foreground-muted">
                {workflows.flows.length} available flows
                {workflows.flows.filter((f) => f.has_schedule).length > 0 &&
                  ` · ${workflows.flows.filter((f) => f.has_schedule).length} scheduled`}
              </p>
              <ul className="space-y-2">
                {workflows.flows.slice(0, 3).map((f) => (
                  <li key={f.id} className="text-sm">
                    <span className="font-medium">{f.id}</span>
                    {f.description && (
                      <span className="ml-2 text-foreground-muted">{f.description}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </QuadrantCard>

        {/* Reports Quadrant */}
        <QuadrantCard
          title="Reports"
          icon={<FileText className="h-5 w-5" />}
          onViewAll={() => onNavigate("reports")}
          isLoading={false}
        >
          <div className="space-y-3">
            <p className="text-sm text-foreground-muted">
              Generate QA reports, approval packages, and regression reports on demand.
            </p>
            <div className="flex gap-2">
              {(["qa", "approval", "regression"] as const).map((type) => (
                <span
                  key={type}
                  className="rounded-full border border-card-border bg-surface-hover px-2.5 py-0.5 text-xs capitalize"
                >
                  {type}
                </span>
              ))}
            </div>
          </div>
        </QuadrantCard>

        {/* Penpot Quadrant */}
        <QuadrantCard
          title="Penpot"
          icon={<Paintbrush className="h-5 w-5" />}
          onViewAll={() => onNavigate("penpot")}
          isLoading={penpotLoading}
        >
          {penpotConns && penpotConns.length > 0 ? (
            <ul className="space-y-2">
              {penpotConns.slice(0, 3).map((c) => (
                <li key={c.id} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[c.status] ?? "bg-foreground-muted"}`} />
                    {c.name}
                  </span>
                  {c.project_name && (
                    <span className="text-foreground-muted">{c.project_name}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-foreground-muted">
              No Penpot connections yet. Connect your first project from Design Sync.
            </p>
          )}
        </QuadrantCard>
      </div>
    </div>
  );
}

function QuadrantCard({
  title,
  icon,
  onViewAll,
  isLoading,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  onViewAll: () => void;
  isLoading: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 font-semibold">
          {icon}
          {title}
        </div>
        <button
          onClick={onViewAll}
          className="text-sm text-interactive hover:underline"
        >
          View All &rarr;
        </button>
      </div>
      {isLoading ? (
        <div className="space-y-2">
          <div className="h-4 w-full animate-pulse rounded bg-surface-hover" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-surface-hover" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-surface-hover" />
        </div>
      ) : (
        children
      )}
    </div>
  );
}
