"use client";

import type { GmailPredictResponse } from "@/types/gmail-intelligence";

const CATEGORY_STYLES: Record<string, string> = {
  Primary: "bg-badge-success-bg text-badge-success-text",
  Promotions: "bg-badge-warning-bg text-badge-warning-text",
  Updates: "bg-badge-info-bg text-badge-info-text",
  Social: "bg-badge-info-bg text-badge-info-text",
  Forums: "bg-surface-muted text-foreground-muted",
};

interface SummaryCardPreviewProps {
  prediction: GmailPredictResponse;
}

export function SummaryCardPreview({ prediction }: SummaryCardPreviewProps) {
  const categoryStyle =
    CATEGORY_STYLES[prediction.predicted_category] ?? CATEGORY_STYLES.Forums;

  return (
    <div className="space-y-2.5">
      {/* Category + confidence */}
      <div className="flex items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${categoryStyle}`}
        >
          {prediction.predicted_category}
        </span>
        <span className="text-[10px] text-foreground-muted">
          {"Confidence"}: {Math.round(prediction.confidence * 100)}%
        </span>
      </div>

      {/* Confidence bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-accent-primary transition-all"
          style={{ width: `${prediction.confidence * 100}%` }}
        />
      </div>

      {/* Summary text */}
      <div>
        <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
          {"AI Summary Preview"}
        </h4>
        <div className="rounded-lg bg-surface-muted p-3">
          <p className="text-sm text-foreground">{prediction.summary_text}</p>
        </div>
      </div>

      {/* Key actions */}
      {prediction.key_actions.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Key Actions"}
          </h4>
          <ul className="space-y-0.5 pl-3">
            {prediction.key_actions.map((action, i) => (
              <li key={i} className="list-disc text-xs text-foreground">
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Promotion signals */}
      {prediction.promotion_signals.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Promotion Signals"}
          </h4>
          <div className="flex flex-wrap gap-1">
            {prediction.promotion_signals.map((signal, i) => (
              <span
                key={i}
                className="rounded-full bg-badge-warning-bg px-2 py-0.5 text-[10px] text-badge-warning-text"
              >
                {signal}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Improvement suggestions */}
      {prediction.improvement_suggestions.length > 0 && (
        <div>
          <h4 className="mb-1 text-[10px] font-medium text-foreground-muted">
            {"Improvement Suggestions"}
          </h4>
          <ol className="space-y-0.5 pl-3">
            {prediction.improvement_suggestions.map((suggestion, i) => (
              <li
                key={i}
                className="list-decimal text-xs text-foreground-muted"
              >
                {suggestion}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
