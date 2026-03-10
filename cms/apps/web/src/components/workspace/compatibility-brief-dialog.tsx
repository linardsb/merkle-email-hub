"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, RefreshCw } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@merkle-email-hub/ui/components/ui/dialog";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@merkle-email-hub/ui/components/ui/accordion";
import { Badge } from "@merkle-email-hub/ui/components/ui/badge";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import {
  useCompatibilityBrief,
  useRegenerateBrief,
} from "@/hooks/use-compatibility-brief";
import type { ClientProfileSchema } from "@merkle-email-hub/sdk";

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
  const t = useTranslations("compatibilityBrief");

  return (
    <AccordionItem value={client.id}>
      <AccordionTrigger className="text-sm hover:no-underline">
        <div className="flex items-center gap-2">
          <span className="font-medium">{client.name}</span>
          <EngineBadge engine={client.engine} />
          <span className="text-muted-foreground">
            {client.unsupported_count > 0
              ? t("unsupportedCount", { count: client.unsupported_count })
              : t("fullSupport")}
          </span>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-3 pb-2">
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>
              {t("platform")}: <span className="text-foreground">{client.platform}</span>
            </span>
            <span>
              {t("engine")}: <span className="text-foreground">{client.engine}</span>
            </span>
            <span>
              {t("marketShare")}: <span className="text-foreground">{client.market_share}%</span>
            </span>
          </div>
          {client.unsupported_properties.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4 font-medium">{t("cssProperty")}</th>
                    <th className="pb-2 pr-4 font-medium">{t("fallback")}</th>
                    <th className="pb-2 font-medium">{t("technique")}</th>
                  </tr>
                </thead>
                <tbody>
                  {client.unsupported_properties.map((prop) => (
                    <tr
                      key={prop.css}
                      className="border-b border-border/50"
                    >
                      <td className="py-1.5 pr-4 font-mono text-foreground">
                        {prop.css}
                      </td>
                      <td className="py-1.5 pr-4 text-muted-foreground">
                        {prop.fallback ?? t("noFallback")}
                      </td>
                      <td className="py-1.5 text-muted-foreground">
                        {prop.technique ?? "—"}
                      </td>
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
  const t = useTranslations("compatibilityBrief");
  const hasClients = targetClients && targetClients.length > 0;
  const { data: brief, isLoading, error, mutate } = useCompatibilityBrief(
    hasClients ? projectId : null
  );
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
          <DialogTitle>{t("title")}</DialogTitle>
          {brief && (
            <DialogDescription>
              {t("description", {
                clientCount: brief.client_count,
                riskyCount: brief.total_risky_properties,
              })}
            </DialogDescription>
          )}
        </DialogHeader>

        {!hasClients && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {t("noClients")}
          </p>
        )}

        {hasClients && isLoading && <LoadingSkeleton />}

        {hasClients && error && (
          <p className="py-8 text-center text-sm text-destructive">
            {t("error")}
          </p>
        )}

        {brief && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">{t("summary")}</h3>
              <div className="flex gap-3">
                <Badge variant="secondary">
                  {t("clientCount", { count: brief.client_count })}
                </Badge>
                <Badge variant="secondary">
                  {t("riskyProperties", { count: brief.total_risky_properties })}
                </Badge>
              </div>

              {brief.dark_mode_warning && (
                <div className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>{t("darkModeWarning")}</p>
                </div>
              )}
            </div>

            {/* Per-Client Profiles */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">{t("clientProfiles")}</h3>
              <Accordion type="multiple" className="w-full">
                {brief.clients.map((client) => (
                  <ClientProfileSection key={client.id} client={client} />
                ))}
              </Accordion>
            </div>

            {/* Risk Matrix */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">{t("riskMatrix")}</h3>
              <p className="text-xs text-muted-foreground">{t("riskMatrixDescription")}</p>
              {brief.risk_matrix.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  {t("noRisks")}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">{t("cssProperty")}</th>
                        <th className="pb-2 pr-4 font-medium">{t("unsupportedIn")}</th>
                        <th className="pb-2 font-medium">{t("fallback")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {brief.risk_matrix.map((entry) => (
                        <tr
                          key={entry.css}
                          className="border-b border-border/50"
                        >
                          <td className="py-1.5 pr-4 font-mono text-foreground">
                            {entry.css}
                          </td>
                          <td className="py-1.5 pr-4">
                            <div className="flex flex-wrap gap-1">
                              {entry.unsupported_in.map((name) => (
                                <span
                                  key={name}
                                  className="rounded bg-destructive/10 px-1 py-0.5 text-[10px] text-destructive"
                                >
                                  {name}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-1.5 text-muted-foreground">
                            {entry.fallback ?? t("noFallback")}
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
              {isRegenerating ? t("regenerating") : t("regenerate")}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            {t("close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
