"use client";

import { AlertTriangle, RefreshCw } from "../icons";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Button } from "@email-hub/ui/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@email-hub/ui/components/ui/accordion";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import { useCompatibilityBrief, useRegenerateBrief } from "@/hooks/use-compatibility-brief";
import type { ClientProfileSchema } from "@email-hub/sdk";

interface CompatibilityBriefDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  targetClients: string[] | null;
}

const ENGINE_STYLES: Record<string, string> = {
  webkit: "bg-accent text-accent-foreground",
  blink: "bg-accent text-accent-foreground",
  word: "bg-destructive/10 text-destructive",
  gecko: "bg-accent text-accent-foreground",
  custom: "bg-muted text-muted-foreground",
};

function EngineBadge({ engine }: { engine: string }) {
  const style = ENGINE_STYLES[engine.toLowerCase()] ?? "bg-muted text-muted-foreground";
  return (
    <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-medium ${style}`}>
      {engine}
    </span>
  );
}

function ClientProfileSection({ client }: { client: ClientProfileSchema }) {
  return (
    <AccordionItem value={client.id}>
      <AccordionTrigger className="text-sm hover:no-underline">
        <div className="flex items-center gap-2">
          <span className="font-medium">{client.name}</span>
          <EngineBadge engine={client.engine} />
          <span className="text-muted-foreground">
            {client.unsupported_count > 0
              ? `${client.unsupported_count} unsupported CSS properties`
              : "Full CSS support"}
          </span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-3 pb-2">
          <div className="text-muted-foreground flex flex-wrap gap-4 text-xs">
            <span>
              {"Platform"}: <span className="text-foreground">{client.platform}</span>
            </span>
            <span>
              {"Engine"}: <span className="text-foreground">{client.engine}</span>
            </span>
            <span>
              {"Market Share"}: <span className="text-foreground">{client.market_share}%</span>
            </span>
          </div>
          {client.unsupported_properties.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-border text-muted-foreground border-b text-left">
                    <th className="pr-4 pb-2 font-medium">{"CSS Property"}</th>
                    <th className="pr-4 pb-2 font-medium">{"Fallback"}</th>
                    <th className="pb-2 font-medium">{"Technique"}</th>
                  </tr>
                </thead>
                <tbody>
                  {client.unsupported_properties.map((prop) => (
                    <tr key={prop.css} className="border-border/50 border-b">
                      <td className="text-foreground py-1.5 pr-4 font-mono">{prop.css}</td>
                      <td className="text-muted-foreground py-1.5 pr-4">
                        {prop.fallback ?? "No fallback available"}
                      </td>
                      <td className="text-muted-foreground py-1.5">{prop.technique ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-4 w-64" />
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-32 w-full" />
    </div>
  );
}

export function CompatibilityBriefDialog({
  open,
  onOpenChange,
  projectId,
  targetClients,
}: CompatibilityBriefDialogProps) {
  const hasClients = targetClients && targetClients.length > 0;
  const {
    data: brief,
    isLoading,
    error,
    mutate,
  } = useCompatibilityBrief(hasClients ? projectId : null);
  const { regenerate, isRegenerating } = useRegenerateBrief(projectId);

  const handleRegenerate = async () => {
    try {
      await regenerate();
      await mutate();
    } catch {
      // Error handled by hook
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-[48rem]">
        <DialogHeader>
          <DialogTitle>{"Compatibility Brief"}</DialogTitle>
          {brief && (
            <DialogDescription>
              {`${brief.client_count} email clients · ${brief.total_risky_properties} risky CSS properties`}
            </DialogDescription>
          )}
        </DialogHeader>

        {!hasClients && (
          <p className="text-muted-foreground py-8 text-center text-sm">
            {
              "No priority clients configured. Set priority clients in project settings to generate a focused compatibility brief, or view the full 25-client matrix."
            }
          </p>
        )}

        {hasClients && isLoading && <LoadingSkeleton />}

        {hasClients && error && (
          <p className="text-destructive py-8 text-center text-sm">
            {"Failed to load compatibility brief"}
          </p>
        )}

        {brief && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="space-y-3">
              <h3 className="text-foreground text-sm font-semibold">{"Summary"}</h3>
              <div className="flex gap-3">
                <Badge variant="secondary">{`${brief.client_count} email clients`}</Badge>
                <Badge variant="secondary">
                  {`${brief.total_risky_properties} risky CSS properties`}
                </Badge>
              </div>

              {brief.dark_mode_warning && (
                <div className="border-destructive/20 bg-destructive/10 text-destructive flex items-start gap-2 rounded-md border p-3 text-sm">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    {
                      "Target audience includes Outlook (Word engine) — requires explicit dark mode overrides via MSO conditionals and color-scheme meta."
                    }
                  </p>
                </div>
              )}
            </div>

            {/* Per-Client Profiles */}
            <div className="space-y-2">
              <h3 className="text-foreground text-sm font-semibold">{"Per-Client Profiles"}</h3>
              <Accordion type="multiple" className="w-full">
                {brief.clients.map((client) => (
                  <ClientProfileSection key={client.id} client={client} />
                ))}
              </Accordion>
            </div>

            {/* Risk Matrix */}
            <div className="space-y-2">
              <h3 className="text-foreground text-sm font-semibold">
                {"Cross-Client Risk Matrix"}
              </h3>
              <p className="text-muted-foreground text-xs">
                {"CSS properties unsupported by 2+ priority clients (highest risk)"}
              </p>
              {brief.risk_matrix.length === 0 ? (
                <p className="text-muted-foreground py-4 text-center text-sm">
                  {"No CSS properties are unsupported across multiple priority clients."}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-border text-muted-foreground border-b text-left">
                        <th className="pr-4 pb-2 font-medium">{"CSS Property"}</th>
                        <th className="pr-4 pb-2 font-medium">{"Unsupported In"}</th>
                        <th className="pb-2 font-medium">{"Fallback"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {brief.risk_matrix.map((entry) => (
                        <tr key={entry.css} className="border-border/50 border-b">
                          <td className="text-foreground py-1.5 pr-4 font-mono">{entry.css}</td>
                          <td className="py-1.5 pr-4">
                            <div className="flex flex-wrap gap-1">
                              {entry.unsupported_in.map((name) => (
                                <span
                                  key={name}
                                  className="bg-destructive/10 text-destructive rounded px-1 py-0.5 text-[10px]"
                                >
                                  {name}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="text-muted-foreground py-1.5">
                            {entry.fallback ?? "No fallback available"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          {hasClients && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerate}
              disabled={isRegenerating}
            >
              <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
              {isRegenerating ? "Regenerating..." : "Regenerate Brief"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            {"Close"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
