"use client";

import { History, Trash2 } from "../../icons";
import { Button } from "@email-hub/ui/components/ui/button";
import { SessionCard } from "./session-card";
import type { ChatSession } from "@/types/chat-history";

interface HistoryPanelProps {
  sessions: ChatSession[];
  onRestore: (session: ChatSession) => void;
  onDelete: (sessionId: string) => void;
  onClearAll: () => void;
}

export function HistoryPanel({ sessions, onRestore, onDelete, onClearAll }: HistoryPanelProps) {
  if (sessions.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-4">
        <div className="text-muted-foreground flex flex-col items-center gap-2">
          <History className="h-5 w-5" />
          <p className="text-sm">{"No conversation history"}</p>
          <p className="text-xs">{"Past conversations will appear here automatically."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-border flex items-center justify-between border-b px-3 py-2">
        <span className="text-muted-foreground text-xs">{`${sessions.length} sessions`}</span>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground h-6 gap-1 px-2 text-[11px]"
          onClick={onClearAll}
        >
          <Trash2 className="h-3 w-3" />
          {"Clear all"}
        </Button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {sessions.map((session) => (
          <SessionCard
            key={session.id}
            session={session}
            onRestore={onRestore}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}
