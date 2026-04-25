"use client";

import type { ModernizationStep } from "@/types/outlook";

const DEP_TYPE_LABELS: Record<string, string> = {
  vml_shape: "VML Shape",
  ghost_table: "Ghost Table",
  mso_conditional: "MSO Conditional",
  mso_css: "MSO CSS",
  dpi_image: "DPI Image",
  external_class: "External Class",
  word_wrap_hack: "Word Wrap Hack",
};

interface MigrationTimelineProps {
  plan: ModernizationStep[];
}

export function MigrationTimeline({ plan }: MigrationTimelineProps) {
  if (plan.length === 0) {
    return <p className="text-foreground-muted text-xs">{"No modernization steps needed"}</p>;
  }

  return (
    <div className="border-border relative ml-3 space-y-3 border-l-2 pl-4">
      {plan.map((step, i) => {
        const depKey = DEP_TYPE_LABELS[step.dependency_type] ?? step.dependency_type;

        return (
          <div key={`${step.dependency_type}-${i}`} className="relative">
            {/* Timeline dot */}
            <div className="border-primary bg-surface-muted text-foreground absolute -left-[25px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 text-[8px] font-bold">
              {i + 1}
            </div>

            <div>
              <p className="text-foreground text-xs font-medium">{step.description}</p>
              <div className="mt-0.5 flex items-center gap-2">
                <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-[10px] font-medium">
                  {depKey}
                </span>
                <span className="text-foreground-muted text-[10px]">
                  {`${step.removals} removals · ${step.byte_savings} bytes saved`}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
