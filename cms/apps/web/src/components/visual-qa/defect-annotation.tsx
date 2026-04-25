"use client";

import { useState } from "react";
import type { DefectAnnotationData } from "@/types/rendering";

interface DefectAnnotationProps {
  defects: DefectAnnotationData[];
  imageWidth: number;
  imageHeight: number;
  containerWidth: number;
  containerHeight: number;
}

const DEFECT_SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  major: "Major",
  minor: "Minor",
  info: "Info",
};

const SEVERITY_STYLES: Record<DefectAnnotationData["severity"], string> = {
  critical: "border-destructive bg-destructive/10",
  major: "border-status-warning bg-status-warning/10",
  minor: "border-foreground-muted bg-foreground-muted/10",
  info: "border-interactive bg-interactive/10",
};

const SEVERITY_BADGE_STYLES: Record<DefectAnnotationData["severity"], string> = {
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
                className="border-border bg-card absolute z-10 w-64 rounded-lg border p-3 shadow-lg"
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
                    {DEFECT_SEVERITY_LABELS[defect.severity] ?? defect.severity}
                  </span>
                </div>
                <p className="text-foreground text-sm">{defect.description}</p>
                {defect.suggested_fix && (
                  <div className="bg-surface-muted mt-2 rounded p-2">
                    <p className="text-foreground-muted text-xs font-medium">{"Suggested Fix"}</p>
                    <p className="text-foreground mt-0.5 text-xs">{defect.suggested_fix}</p>
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
