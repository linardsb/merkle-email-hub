"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { RenderingTest, RenderingResult } from "@/types/rendering";

interface Props {
  tests: RenderingTest[];
  onScreenshotClick: (result: RenderingResult, clientName: string) => void;
}

function statusBadge(status: string, t: (key: string) => string) {
  const styles: Record<string, string> = {
    completed: "bg-badge-success-bg text-badge-success-text",
    failed: "bg-badge-danger-bg text-badge-danger-text",
    processing: "bg-badge-warning-bg text-badge-warning-text",
    queued: "bg-badge-neutral-bg text-badge-neutral-text",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? styles.queued}`}>
      {t(status)}
    </span>
  );
}

function resultStatusBadge(status: string) {
  const styles: Record<string, string> = {
    pass: "bg-status-success",
    warning: "bg-status-warning",
    fail: "bg-status-danger",
    pending: "bg-surface-muted",
  };
  return styles[status] ?? styles.pending;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RenderingTestList({ tests, onScreenshotClick }: Props) {
  const t = useTranslations("renderings");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <div className="rounded-lg border border-card-border bg-card-bg p-6">
      <h2 className="text-lg font-semibold text-foreground">{t("recentTests")}</h2>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-card-border">
              <th className="w-8 pb-2" />
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("status")}</th>
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("template")}</th>
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("provider")}</th>
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("compatibility")}</th>
              <th className="pb-2 pr-4 text-left font-medium text-foreground-muted">{t("clients")}</th>
              <th className="pb-2 text-left font-medium text-foreground-muted">{t("date")}</th>
            </tr>
          </thead>
          <tbody>
            {tests.map((test) => {
              const isExpanded = expandedId === test.id;
              return (
                <tr key={test.id} className="group">
                  <td colSpan={7} className="p-0">
                    <button
                      className="flex w-full items-center border-b border-card-border/50 py-3 text-left hover:bg-surface-muted/30"
                      onClick={() => setExpandedId(isExpanded ? null : test.id)}
                    >
                      <span className="w-8 flex-shrink-0 px-2">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-foreground-muted" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-foreground-muted" />
                        )}
                      </span>
                      <span className="w-24 flex-shrink-0 pr-4">{statusBadge(test.status, t)}</span>
                      <span className="min-w-0 flex-1 pr-4 font-medium text-foreground">{test.template_name}</span>
                      <span className="w-28 flex-shrink-0 pr-4 capitalize text-foreground-muted">
                        {test.provider === "email_on_acid" ? t("emailOnAcid") : t("litmus")}
                      </span>
                      <span className="w-20 flex-shrink-0 pr-4 font-medium text-foreground">{test.compatibility_score}%</span>
                      <span className="w-16 flex-shrink-0 pr-4 text-foreground-muted">{test.results.length}</span>
                      <span className="w-32 flex-shrink-0 text-foreground-muted">{formatDate(test.created_at)}</span>
                    </button>

                    {isExpanded && (
                      <div className="border-b border-card-border bg-surface-muted/20 p-4">
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                          {test.results.map((result) => (
                            <button
                              key={result.client_id}
                              className="group/thumb relative overflow-hidden rounded-md border border-card-border bg-card-bg transition-shadow hover:shadow-md"
                              onClick={() =>
                                onScreenshotClick(result, result.client_id.replace(/_/g, " "))
                              }
                            >
                              <img
                                src={result.screenshot_url}
                                alt={result.client_id}
                                className="aspect-[3/2] w-full object-cover"
                                loading="lazy"
                              />
                              <div className="flex items-center justify-between p-2">
                                <span className="truncate text-xs capitalize text-foreground">
                                  {result.client_id.replace(/_/g, " ")}
                                </span>
                                <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${resultStatusBadge(result.status)}`} />
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
