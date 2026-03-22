"use client";

import { CLIENT_DISPLAY_NAMES, type ClientProfile } from "@/types/rendering";

interface ClientResult {
  client_id: string;
  score: number;
  market_share: number;
}

interface ConfidenceSummaryBarProps {
  clientResults: ClientResult[];
  overallScore: number;
}

function getTierColor(score: number): string {
  if (score >= 85) return "bg-status-success";
  if (score >= 60) return "bg-status-warning";
  return "bg-status-danger";
}

export function ConfidenceSummaryBar({
  clientResults,
  overallScore,
}: ConfidenceSummaryBarProps) {
  const totalShare = clientResults.reduce((sum, r) => sum + r.market_share, 0);

  return (
    <div className="space-y-2">
      {/* Segmented bar */}
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-surface-muted">
        {clientResults.map((r) => {
          const widthPct = totalShare > 0 ? (r.market_share / totalShare) * 100 : 0;
          const displayName =
            CLIENT_DISPLAY_NAMES[r.client_id as ClientProfile] ?? r.client_id;
          return (
            <span
              key={r.client_id}
              className={`${getTierColor(r.score)} transition-all first:rounded-l-full last:rounded-r-full`}
              style={{ width: `${widthPct}%` }}
              title={`${displayName}: ${r.score.toFixed(0)}%`}
            />
          );
        })}
      </div>

      {/* Overall score label */}
      <p className="text-sm text-foreground-muted">
        Overall rendering confidence:{" "}
        <span className="font-medium text-foreground">{overallScore.toFixed(0)}%</span>
      </p>
    </div>
  );
}
