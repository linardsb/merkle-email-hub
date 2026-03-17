"use client";

import { useTranslations } from "next-intl";
import type { ModernizationStep } from "@/types/outlook";

interface MigrationTimelineProps {
  plan: ModernizationStep[];
}

export function MigrationTimeline({ plan }: MigrationTimelineProps) {
  const t = useTranslations("outlookAdvisor");

  if (plan.length === 0) {
    return (
      <p className="text-xs text-foreground-muted">{t("noMigrationSteps")}</p>
    );
  }

  return (
    <div className="relative ml-3 border-l-2 border-border pl-4 space-y-3">
      {plan.map((step, i) => {
        let depKey: string;
        try {
          depKey = t(`depTypes.${step.dependency_type}`);
        } catch {
          depKey = step.dependency_type;
        }

        return (
          <div key={`${step.dependency_type}-${i}`} className="relative">
            {/* Timeline dot */}
            <div className="absolute -left-[25px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-primary bg-surface-muted text-[8px] font-bold text-foreground">
              {i + 1}
            </div>

            <div>
              <p className="text-xs font-medium text-foreground">
                {step.description}
              </p>
              <div className="mt-0.5 flex items-center gap-2">
                <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[10px] font-medium text-foreground-muted">
                  {depKey}
                </span>
                <span className="text-[10px] text-foreground-muted">
                  {t("stepRemovals", {
                    removals: step.removals,
                    savings: step.byte_savings,
                  })}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
