"use client";

import type { ConfidenceBreakdown } from "@/types/rendering-dashboard";

interface ConfidenceBarProps {
  score: number; // 0-100
  threshold?: number; // 0-100, optional threshold marker
  label?: string;
  breakdown?: ConfidenceBreakdown;
  size?: "sm" | "md"; // sm=h-2 (default), md=h-3
}

function getBarColor(score: number): string {
  if (score >= 85) return "bg-status-success";
  if (score >= 60) return "bg-status-warning";
  return "bg-status-danger";
}

function formatBreakdownTitle(breakdown: ConfidenceBreakdown): string {
  return [
    `Emulator coverage: ${(breakdown.emulator_coverage * 100).toFixed(0)}%`,
    `CSS compatibility: ${(breakdown.css_compatibility * 100).toFixed(0)}%`,
    `Calibration accuracy: ${(breakdown.calibration_accuracy * 100).toFixed(0)}%`,
    `Layout complexity: ${(breakdown.layout_complexity * 100).toFixed(0)}%`,
  ].join("\n");
}

export function ConfidenceBar({
  score,
  threshold,
  label,
  breakdown,
  size = "sm",
}: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const heightClass = size === "md" ? "h-3" : "h-2";

  return (
    <span
      className="relative flex-1"
      title={breakdown ? formatBreakdownTitle(breakdown) : undefined}
      aria-label={label ?? `Confidence: ${clamped.toFixed(0)}%`}
    >
      <span className={`block ${heightClass} bg-surface-muted w-full rounded-full`}>
        <span
          className={`block ${heightClass} rounded-full ${getBarColor(clamped)} transition-all`}
          style={{ width: `${clamped}%` }}
        />
      </span>
      {threshold != null && (
        <span
          className={`absolute top-0 ${heightClass} bg-foreground-muted w-0.5`}
          style={{ left: `${Math.max(0, Math.min(100, threshold))}%` }}
          title={`Threshold: ${threshold}%`}
        />
      )}
    </span>
  );
}
