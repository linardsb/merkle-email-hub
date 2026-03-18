"use client";

import { CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import { useComponentCompatibility } from "@/hooks/use-components";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";

interface CompatibilityMatrixProps {
  componentId: number;
}

const LEVEL_NONE = { icon: XCircle, style: "text-status-danger" } as const;

const LEVEL_CONFIG: Record<string, { icon: typeof CheckCircle2; style: string }> = {
  full: { icon: CheckCircle2, style: "text-status-success" },
  partial: { icon: AlertTriangle, style: "text-status-warning" },
  none: LEVEL_NONE,
};

type ClientEntry = { client_id: string; client_name: string; level: string; platform: string };

function groupByFamily(clients: ClientEntry[]) {
  const groups: Record<string, ClientEntry[]> = {};
  for (const client of clients) {
    const family = (client.client_name.split(/\s*[(/]/)[0] ?? client.client_name).replace(/\s*\d{4}.*/, "").trim();
    (groups[family] ??= []).push(client);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
}

export function CompatibilityMatrix({ componentId }: CompatibilityMatrixProps) {
  const { data, isLoading, error } = useComponentCompatibility(componentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-foreground-muted">{"No compatibility data available. Run QA to generate."}</p>
      </div>
    );
  }

  const groups = groupByFamily(data.clients);

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="h-4 w-4 text-status-success" />
          <span className="text-sm text-foreground">
            {`\${data.full_count} full`}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="h-4 w-4 text-status-warning" />
          <span className="text-sm text-foreground">
            {`\${data.partial_count} partial`}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle className="h-4 w-4 text-status-danger" />
          <span className="text-sm text-foreground">
            {`\${data.none_count} unsupported`}
          </span>
        </div>
        {data.qa_score != null && (
          <span className="ml-auto text-sm text-foreground-muted">
            {`QA Score: \${Math.round(data.qa_score * 100)}%`}
          </span>
        )}
      </div>

      {/* Client matrix grouped by family */}
      <ScrollArea className="max-h-96">
        <div className="space-y-3">
          {groups.map(([family, clients]) => (
            <div key={family}>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
                {family}
              </h4>
              <div className="space-y-1">
                {clients.map((client) => {
                  const config = LEVEL_CONFIG[client.level] ?? LEVEL_NONE;
                  const Icon = config.icon;
                  const iconStyle = config.style;
                  return (
                    <div
                      key={client.client_id}
                      className="flex items-center justify-between rounded-md px-3 py-1.5 hover:bg-surface-hover"
                    >
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${iconStyle}`} />
                        <span className="text-sm text-foreground">{client.client_name}</span>
                      </div>
                      <span className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted">
                        {client.platform}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {data.last_checked && (
        <p className="text-xs text-foreground-muted">
          {`Last checked: \${new Date(data.last_checked).toLocaleDateString()}`}
        </p>
      )}
    </div>
  );
}
