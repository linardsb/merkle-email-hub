"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, KeyRound } from "../icons";
import { useCredentialHealth, type ServiceHealth } from "@/hooks/use-credentials-health";

const STATUS_DOT: Record<string, string> = {
  healthy: "bg-status-success",
  cooled_down: "bg-status-warning",
  unhealthy: "bg-status-error",
};

const STATUS_LABEL: Record<string, string> = {
  healthy: "Healthy",
  cooled_down: "Cooled down",
  unhealthy: "Unhealthy",
};

export function CredentialHealthCard() {
  const { data, isLoading } = useCredentialHealth();

  if (isLoading) {
    return (
      <div className="border-card-border bg-card-bg rounded-lg border p-6">
        <div className="mb-4 flex items-center gap-2 font-semibold">
          <KeyRound className="h-5 w-5" />
          Credentials
        </div>
        <div className="space-y-2">
          <div className="bg-surface-hover h-4 w-full animate-pulse rounded" />
          <div className="bg-surface-hover h-4 w-3/4 animate-pulse rounded" />
          <div className="bg-surface-hover h-4 w-1/2 animate-pulse rounded" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="border-card-border bg-card-bg rounded-lg border p-6">
      <div className="mb-4 flex items-center gap-2 font-semibold">
        <KeyRound className="h-5 w-5" />
        Credentials
      </div>
      <div className="space-y-3">
        {/* Summary dots */}
        <div className="flex gap-3 text-sm">
          <span className="flex items-center gap-1">
            <span className="bg-status-success inline-block h-2 w-2 rounded-full" />
            {data.healthy_total ?? 0} healthy
          </span>
          <span className="flex items-center gap-1">
            <span className="bg-status-warning inline-block h-2 w-2 rounded-full" />
            {data.cooled_down_total ?? 0} cooled down
          </span>
          <span className="flex items-center gap-1">
            <span className="bg-status-error inline-block h-2 w-2 rounded-full" />
            {data.unhealthy_total ?? 0} unhealthy
          </span>
        </div>

        {/* Per-service breakdown */}
        {!data.services || data.services.length === 0 ? (
          <p className="text-foreground-muted text-sm">No credential pools configured.</p>
        ) : (
          <ul className="space-y-2">
            {data.services.map((svc) => (
              <ServiceRow key={svc.service} service={svc} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function ServiceRow({ service }: { service: ServiceHealth }) {
  const [expanded, setExpanded] = useState(false);

  const overallStatus =
    service.unhealthy > 0 ? "unhealthy" : service.cooled_down > 0 ? "cooled_down" : "healthy";

  return (
    <li>
      <button
        onClick={() => setExpanded(!expanded)}
        className="hover:bg-surface-hover flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm"
      >
        <span className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="text-foreground-muted h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="text-foreground-muted h-3.5 w-3.5" />
          )}
          <span
            className={`inline-block h-2 w-2 rounded-full ${STATUS_DOT[overallStatus] ?? "bg-foreground-muted"}`}
          />
          <span className="font-medium">{service.service}</span>
        </span>
        <span className="text-foreground-muted">
          {service.healthy}/{service.key_count} keys healthy
        </span>
      </button>

      {expanded && (
        <ul className="ml-8 mt-1 space-y-1">
          {service.keys.map((key) => (
            <li
              key={key.key_hash}
              className="flex items-center justify-between rounded px-2 py-1 text-xs"
            >
              <span className="flex items-center gap-2">
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${STATUS_DOT[key.status] ?? "bg-foreground-muted"}`}
                />
                <code className="text-foreground-muted">{key.key_hash}</code>
              </span>
              <span className="text-foreground-muted flex items-center gap-3">
                <span>{STATUS_LABEL[key.status] ?? key.status}</span>
                {key.failure_count > 0 && <span>{key.failure_count} failures</span>}
                {key.cooldown_remaining_s > 0 && (
                  <span>{Math.round(key.cooldown_remaining_s)}s cooldown</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
