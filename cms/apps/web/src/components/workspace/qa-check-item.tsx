"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import type { QACheckResult } from "@/types/qa";

interface QACheckItemProps {
  check: QACheckResult;
  isOverridden?: boolean;
}

export function QACheckItem({ check, isOverridden }: QACheckItemProps) {
  const t = useTranslations("qa");
  const i18nKey = `check_${check.check_name}`;
  const label = t.has(i18nKey as Parameters<typeof t>[0])
    ? t(i18nKey as Parameters<typeof t>[0])
    : check.check_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const scorePercent = Math.round(check.score * 100);

  return (
    <div className="flex items-start gap-3 rounded-md border border-border px-3 py-2.5">
      {/* Status icon */}
      <div className="mt-0.5 shrink-0">
        {check.passed ? (
          <CheckCircle2 className="h-4 w-4 text-status-success" />
        ) : isOverridden ? (
          <AlertTriangle className="h-4 w-4 text-status-warning" />
        ) : (
          <XCircle className="h-4 w-4 text-destructive" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">
            {label}
            {isOverridden && (
              <span className="ml-2 text-xs text-status-warning">
                {t("overridden")}
              </span>
            )}
          </span>
          <span className="text-xs text-muted-foreground">{scorePercent}%</span>
        </div>

        {/* Score bar */}
        <div className="mt-1.5 h-1 w-full rounded-full bg-muted">
          <div
            className={`h-1 rounded-full transition-all ${
              check.passed
                ? "bg-status-success"
                : isOverridden
                  ? "bg-status-warning"
                  : "bg-destructive"
            }`}
            style={{ width: `${scorePercent}%` }}
          />
        </div>

        {/* Details (only for failures) */}
        {!check.passed && check.details && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            {check.details}
          </p>
        )}
      </div>
    </div>
  );
}
