"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { DefectAnnotationData } from "@/types/rendering";

interface DefectAnnotationProps {
  defects: DefectAnnotationData[];
  imageWidth: number;
  imageHeight: number;
  containerWidth: number;
  containerHeight: number;
}

const SEVERITY_STYLES: Record<
  DefectAnnotationData["severity"],
  string
> = {
  critical: "border-destructive bg-destructive/10",
  major: "border-status-warning bg-status-warning/10",
  minor: "border-foreground-muted bg-foreground-muted/10",
  info: "border-interactive bg-interactive/10",
};

const SEVERITY_BADGE_STYLES: Record<
  DefectAnnotationData["severity"],
  string
> = {
  critical: "bg-badge-danger-bg text-badge-danger-text",
  major: "bg-badge-warning-bg text-badge-warning-text",
  minor: "bg-surface-muted text-foreground-muted",
  info: "bg-interactive/10 text-interactive",
};

/**
 * Stub component for VLM defect annotations.
 * Renders clickable region overlays on a screenshot container.
 * Not wired to backend yet — pass empty defects array.
 */
export function DefectAnnotation({
  defects,
  imageWidth,
  imageHeight,
  containerWidth,
  containerHeight,
}: DefectAnnotationProps) {
  const t = useTranslations("visualQa");
  const [activeDefect, setActiveDefect] = useState<number | null>(null);

  if (defects.length === 0) return null;

  const scaleX = containerWidth / imageWidth;
  const scaleY = containerHeight / imageHeight;

  return (
    <>
      {defects.map((defect, index) => {
        const left = defect.region.x * scaleX;
        const top = defect.region.y * scaleY;
        const width = defect.region.width * scaleX;
        const height = defect.region.height * scaleY;
        const isActive = activeDefect === index;

        return (
          <div key={index}>
            {/* Region overlay */}
            <button
              type="button"
              onClick={() => setActiveDefect(isActive ? null : index)}
              className={`absolute cursor-pointer rounded border-2 transition-opacity ${
                SEVERITY_STYLES[defect.severity]
              } ${isActive ? "opacity-100" : "opacity-60 hover:opacity-100"}`}
              style={{ left, top, width, height }}
              aria-label={defect.description}
            />

            {/* Tooltip */}
            {isActive && (
              <div
                className="absolute z-10 w-64 rounded-lg border border-border bg-card p-3 shadow-lg"
                style={{
                  left: left + width + 8,
                  top,
                }}
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      SEVERITY_BADGE_STYLES[defect.severity]
                    }`}
                  >
                    {t(`defect${defect.severity.charAt(0).toUpperCase()}${defect.severity.slice(1)}` as
                      | "defectCritical"
                      | "defectMajor"
                      | "defectMinor"
                      | "defectInfo")}
                  </span>
                </div>
                <p className="text-sm text-foreground">
                  {defect.description}
                </p>
                {defect.suggested_fix && (
                  <div className="mt-2 rounded bg-surface-muted p-2">
                    <p className="text-xs font-medium text-foreground-muted">
                      {t("suggestedFix")}
                    </p>
                    <p className="mt-0.5 text-xs text-foreground">
                      {defect.suggested_fix}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}
