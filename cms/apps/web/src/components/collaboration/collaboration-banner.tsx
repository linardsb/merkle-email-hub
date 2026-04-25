"use client";

import { Users } from "../icons";
import type { Collaborator, CollaborationStatus } from "@/types/collaboration";

interface CollaborationBannerProps {
  collaborators: Collaborator[];
  status: CollaborationStatus;
  isViewOnly?: boolean;
  onTogglePresencePanel: () => void;
}

const STATUS_DOT: Record<CollaborationStatus, string> = {
  connected: "bg-success",
  connecting: "bg-warning animate-pulse",
  disconnected: "bg-destructive",
};

export function CollaborationBanner({
  collaborators,
  status,
  isViewOnly,
  onTogglePresencePanel,
}: CollaborationBannerProps) {
  const editingCount = collaborators.filter((c) => c.activity === "editing").length;
  const maxAvatars = 3;
  const visible = collaborators.slice(0, maxAvatars);
  const overflow = collaborators.length - maxAvatars;

  return (
    <button
      type="button"
      onClick={onTogglePresencePanel}
      className="hover:bg-accent flex items-center gap-2 rounded px-2 py-1 text-xs transition-colors"
    >
      {/* Connection dot */}
      <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[status]}`} />

      {/* Avatar stack */}
      {visible.length > 0 && (
        <div className="flex -space-x-1.5">
          {visible.map((c) => (
            <div
              key={c.clientId}
              className="border-card flex h-5 w-5 items-center justify-center rounded-full border text-[9px] font-medium text-white"
              style={{ backgroundColor: c.color }}
            >
              {c.name.charAt(0).toUpperCase()}
            </div>
          ))}
          {overflow > 0 && (
            <div className="border-card bg-muted text-foreground flex h-5 w-5 items-center justify-center rounded-full border text-[9px] font-medium">
              +{overflow}
            </div>
          )}
        </div>
      )}

      {/* Label */}
      <span className="text-muted-foreground">
        {editingCount > 0
          ? `${editingCount} editing`
          : collaborators.length > 0
            ? `${collaborators.length} viewing`
            : "Only you"}
      </span>

      {/* View-only badge */}
      {isViewOnly && (
        <span className="bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px] font-medium">
          {"View only"}
        </span>
      )}

      <Users className="text-muted-foreground h-3.5 w-3.5" />
    </button>
  );
}
