"use client";

import { CheckCircle2, AlertTriangle, XCircle, Loader2 } from "../icons";
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
    const family = (client.client_name.split(/\s*[(/]/)[0] ?? client.client_name)
      .replace(/\s*\d{4}.*/, "")
      .trim();
    (groups[family] ??= []).push(client);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
}

export function CompatibilityMatrix({ componentId }: CompatibilityMatrixProps) {
  const { data, isLoading, error } = useComponentCompatibility(componentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="text-foreground-muted h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-8 text-center">
        <p className="text-foreground-muted text-sm">
          {"No compatibility data available. Run QA to generate."}
        </p>
      </div>
    );
  }

  const groups = groupByFamily(data.clients);

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="text-status-success h-4 w-4" />
          <span className="text-foreground text-sm">{`${data.full_count} full`}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="text-status-warning h-4 w-4" />
          <span className="text-foreground text-sm">{`${data.partial_count} partial`}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle className="text-status-danger h-4 w-4" />
          <span className="text-foreground text-sm">{`${data.none_count} unsupported`}</span>
        </div>
        {data.qa_score != null && (
          <span className="text-foreground-muted ml-auto text-sm">
            {`QA Score: ${Math.round(data.qa_score * 100)}%`}
          </span>
        )}
      </div>

      {/* Client matrix grouped by family */}
      <ScrollArea className="max-h-96">
        <div className="space-y-3">
          {groups.map(([family, clients]) => (
            <div key={family}>
              <h4 className="text-foreground-muted mb-1.5 text-xs font-semibold uppercase tracking-wide">
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
                      className="hover:bg-surface-hover flex items-center justify-between rounded-md px-3 py-1.5"
                    >
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${iconStyle}`} />
                        <span className="text-foreground text-sm">{client.client_name}</span>
                      </div>
                      <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-xs">
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
        <p className="text-foreground-muted text-xs">
          {`Last checked: ${new Date(data.last_checked).toLocaleDateString()}`}
        </p>
      )}
    </div>
  );
}
