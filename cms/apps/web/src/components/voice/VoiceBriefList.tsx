"use client";

import { useState } from "react";
import { Mic, Inbox } from "lucide-react";
import { useVoiceBriefs } from "@/hooks/use-voice-briefs";
import { VoiceBriefCard } from "./VoiceBriefCard";
import { VoiceBriefDetail } from "./VoiceBriefDetail";

interface VoiceBriefListProps {
  projectId: number;
}

export function VoiceBriefList({ projectId }: VoiceBriefListProps) {
  const [selectedBriefId, setSelectedBriefId] = useState<number | null>(null);
  const { data, isLoading } = useVoiceBriefs(projectId);

  const briefs = data?.items ?? [];
  const pendingCount = briefs.filter((b) => b.status === "pending").length;
  const readyCount = briefs.filter((b) => b.status === "extracted").length;

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Mic className="h-4 w-4 text-interactive" />
          {"Voice Briefs"}
          {readyCount > 0 && (
            <span className="rounded-full bg-badge-success-bg px-2 py-0.5 text-[10px] font-medium text-badge-success-text">
              {readyCount} {"ready"}
            </span>
          )}
          {pendingCount > 0 && (
            <span className="rounded-full bg-badge-warning-bg px-2 py-0.5 text-[10px] font-medium text-badge-warning-text animate-pulse">
              {pendingCount} {"processing"}
            </span>
          )}
        </h3>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-skeleton" />
          ))}
        </div>
      ) : briefs.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-8 text-center">
          <Inbox className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">{"No voice briefs yet"}</p>
          <p className="text-xs text-muted-foreground/60">{"Briefs will appear here when clients submit them"}</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {briefs.map((brief) => (
            <VoiceBriefCard
              key={brief.id}
              brief={brief}
              onSelect={setSelectedBriefId}
            />
          ))}
        </div>
      )}

      {/* Detail dialog */}
      {selectedBriefId != null && (
        <VoiceBriefDetail
          projectId={projectId}
          briefId={selectedBriefId}
          open
          onOpenChange={(open) => {
            if (!open) setSelectedBriefId(null);
          }}
        />
      )}
    </div>
  );
}
