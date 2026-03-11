"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";
import { Badge } from "@email-hub/ui/components/ui/badge";

const REVIEW_THRESHOLD = 0.5;

interface ConfidenceIndicatorProps {
  confidence: number;
  showReviewBadge?: boolean;
}

export function ConfidenceIndicator({ confidence, showReviewBadge = true }: ConfidenceIndicatorProps) {
  const t = useTranslations("workspace");
  const pct = Math.round(confidence * 100);

  const colorClass =
    confidence > 0.8
      ? "text-chart-2"
      : confidence >= REVIEW_THRESHOLD
        ? "text-muted-foreground"
        : "text-destructive";

  const needsReview = confidence < REVIEW_THRESHOLD;

  return (
    <div className="mt-1.5 flex items-center gap-1.5">
      <span className={`text-[10px] font-medium ${colorClass}`}>
        {t("chatConfidence", { pct })}
      </span>
      {needsReview && showReviewBadge && (
        <Badge variant="destructive" className="gap-1 px-1.5 py-0 text-[10px]">
          <AlertTriangle className="h-2.5 w-2.5" />
          {t("chatNeedsReview")}
        </Badge>
      )}
    </div>
  );
}
