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
  const categoryStyle = CATEGORY_STYLES[prediction.predicted_category] ?? CATEGORY_STYLES.Forums;

  return (
    <div className="space-y-2.5">
      {/* Category + confidence */}
      <div className="flex items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${categoryStyle}`}>
          {prediction.predicted_category}
        </span>
        <span className="text-foreground-muted text-[10px]">
          {"Confidence"}: {Math.round(prediction.confidence * 100)}%
        </span>
      </div>

      {/* Confidence bar */}
      <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
        <div
          className="bg-accent-primary h-full rounded-full transition-all"
          style={{ width: `${prediction.confidence * 100}%` }}
        />
      </div>

      {/* Summary text */}
      <div>
        <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
          {"AI Summary Preview"}
        </h4>
        <div className="bg-surface-muted rounded-lg p-3">
          <p className="text-foreground text-sm">{prediction.summary_text}</p>
        </div>
      </div>

      {/* Key actions */}
      {prediction.key_actions.length > 0 && (
        <div>
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">{"Key Actions"}</h4>
          <ul className="space-y-0.5 pl-3">
            {prediction.key_actions.map((action, i) => (
              <li key={i} className="text-foreground list-disc text-xs">
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Promotion signals */}
      {prediction.promotion_signals.length > 0 && (
        <div>
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
            {"Promotion Signals"}
          </h4>
          <div className="flex flex-wrap gap-1">
            {prediction.promotion_signals.map((signal, i) => (
              <span
                key={i}
                className="bg-badge-warning-bg text-badge-warning-text rounded-full px-2 py-0.5 text-[10px]"
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
          <h4 className="text-foreground-muted mb-1 text-[10px] font-medium">
            {"Improvement Suggestions"}
          </h4>
          <ol className="space-y-0.5 pl-3">
            {prediction.improvement_suggestions.map((suggestion, i) => (
              <li key={i} className="text-foreground-muted list-decimal text-xs">
                {suggestion}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
