"use client";

import { Eye, UserRoundPen, Moon, X } from "lucide-react";
import type { Collaborator, FollowTarget } from "@/types/collaboration";

interface PresencePanelProps {
  collaborators: Collaborator[];
  followTarget: FollowTarget | null;
  onFollow: (clientId: number, name: string) => void;
  onUnfollow: () => void;
  onClose: () => void;
}

const ACTIVITY_ICON = {
  editing: UserRoundPen,
  idle: Moon,
  viewing: Eye,
} as const;

const ACTIVITY_STYLE = {
  editing: "text-success animate-pulse",
  idle: "text-muted-foreground",
  viewing: "text-interactive",
} as const;

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  developer: "Developer",
  viewer: "Viewer",
};

const ACTIVITY_LABELS: Record<string, string> = {
  editing: "Editing",
  idle: "Idle",
  viewing: "Viewing",
};

export function PresencePanel({
  collaborators,
  followTarget,
  onFollow,
  onUnfollow,
  onClose,
}: PresencePanelProps) {
  return (
    <div className="flex h-full w-64 flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-xs font-semibold text-foreground">
          {"Collaborators"}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* User list */}
      <div className="flex-1 overflow-y-auto p-2">
        {collaborators.length === 0 ? (
          <p className="px-2 py-4 text-center text-xs text-muted-foreground">
            {"No one else is here"}
          </p>
        ) : (
          <ul className="space-y-1">
            {collaborators.map((collab) => {
              const ActivityIcon = ACTIVITY_ICON[collab.activity];
              const isFollowed = followTarget?.clientId === collab.clientId;

              return (
                <li
                  key={collab.clientId}
                  className="flex items-center gap-2 rounded px-2 py-1.5 text-xs transition-colors hover:bg-accent"
                >
                  {/* Avatar */}
                  <div
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-medium text-white"
                    style={{ backgroundColor: collab.color }}
                  >
                    {collab.name.charAt(0).toUpperCase()}
                  </div>

                  {/* Name + role */}
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate font-medium text-foreground">
                      {collab.name}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {ROLE_LABELS[collab.role] ?? collab.role}
                    </span>
                  </div>

                  {/* Activity indicator */}
                  <ActivityIcon
                    className={`h-3.5 w-3.5 shrink-0 ${ACTIVITY_STYLE[collab.activity]}`}
                    aria-label={ACTIVITY_LABELS[collab.activity]}
                  />

                  {/* Follow button */}
                  <button
                    type="button"
                    onClick={() =>
                      isFollowed
                        ? onUnfollow()
                        : onFollow(collab.clientId, collab.name)
                    }
                    className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] transition-colors ${
                      isFollowed
                        ? "bg-interactive text-on-interactive"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    {isFollowed ? "Following" : "Follow"}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
