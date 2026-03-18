"use client";

import { Mic, Clock, ChevronRight, AlertCircle } from "lucide-react";
import type { VoiceBriefSummary } from "@/hooks/use-voice-briefs";

interface VoiceBriefCardProps {
  brief: VoiceBriefSummary;
  onSelect: (briefId: number) => void;
}

export function VoiceBriefCard({ brief, onSelect }: VoiceBriefCardProps) {
  const statusConfig: Record<string, { label: string; className: string }> = {
    pending: {
      label: "Processing",
      className: "bg-badge-warning-bg text-badge-warning-text",
    },
    transcribed: {
      label: "Transcribed",
      className: "bg-badge-info-bg text-badge-info-text",
    },
    extracted: {
      label: "Ready",
      className: "bg-badge-success-bg text-badge-success-text",
    },
    failed: {
      label: "Failed",
      className: "bg-badge-danger-bg text-badge-danger-text",
    },
  };

  const status = statusConfig[brief.status] ?? {
    label: "Processing",
    className: "bg-badge-warning-bg text-badge-warning-text",
  };

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <button
      type="button"
      onClick={() => onSelect(brief.id)}
      disabled={brief.status === "pending"}
      className="flex w-full items-center gap-3 rounded-lg border border-default bg-card p-3 text-left transition-colors hover:bg-accent disabled:opacity-60 disabled:cursor-wait"
    >
      {/* Icon */}
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-muted">
        {brief.status === "failed" ? (
          <AlertCircle className="h-4 w-4 text-status-danger" />
        ) : (
          <Mic className="h-4 w-4 text-interactive" />
        )}
      </div>

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {brief.brief_topic ?? "Untitled Brief"}
          </span>
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${status.className}`}>
            {status.label}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{brief.submitted_by}</span>
          {brief.duration_seconds != null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDuration(brief.duration_seconds)}
            </span>
          )}
          <span>{timeAgo(brief.created_at)}</span>
          {brief.confidence != null && (
            <span>{Math.round(brief.confidence * 100)}%</span>
          )}
        </div>
      </div>

      {/* Chevron */}
      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
    </button>
  );
}
