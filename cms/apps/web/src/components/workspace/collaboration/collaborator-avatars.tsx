"use client";

import type { Collaborator } from "@/types/collaboration";

interface CollaboratorAvatarsProps {
  collaborators: Collaborator[];
  maxVisible?: number;
}

export function CollaboratorAvatars({ collaborators, maxVisible = 3 }: CollaboratorAvatarsProps) {
  if (collaborators.length === 0) return null;

  const visible = collaborators.slice(0, maxVisible);
  const overflow = collaborators.length - maxVisible;

  return (
    <div className="flex items-center -space-x-1.5">
      {visible.map((collab) => (
        <div
          key={collab.clientId}
          className="border-card flex h-6 w-6 items-center justify-center rounded-full border-2 text-[10px] font-medium text-white"
          style={{ backgroundColor: collab.color }}
          title={collab.name}
        >
          {collab.name.charAt(0).toUpperCase()}
        </div>
      ))}
      {overflow > 0 && (
        <div className="border-card bg-muted text-foreground flex h-6 w-6 items-center justify-center rounded-full border-2 text-[10px] font-medium">
          +{overflow}
        </div>
      )}
    </div>
  );
}
