"use client";

import { CheckCircle2, AlertTriangle, XCircle } from "../icons";
import type { GateVerdict } from "@/types/rendering-gate";

const VERDICT_STYLES: Record<
  GateVerdict,
  { bg: string; text: string; icon: typeof CheckCircle2; label: string }
> = {
  pass: {
    bg: "bg-badge-success-bg",
    text: "text-badge-success-text",
    icon: CheckCircle2,
    label: "All Clients Pass",
  },
  warn: {
    bg: "bg-badge-warning-bg",
    text: "text-badge-warning-text",
    icon: AlertTriangle,
    label: "Warnings",
  },
  block: {
    bg: "bg-badge-danger-bg",
    text: "text-badge-danger-text",
    icon: XCircle,
    label: "Blocked",
  },
};

interface Props {
  verdict: GateVerdict;
  blockingCount?: number;
}

export function GateSummaryBadge({ verdict, blockingCount }: Props) {
  const style = VERDICT_STYLES[verdict];
  const Icon = style.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${style.bg} ${style.text}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {style.label}
      {verdict === "block" && blockingCount ? ` (${blockingCount})` : ""}
    </span>
  );
}
