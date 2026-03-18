"use client";

import { RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@email-hub/ui/components/ui/button";
import { Badge } from "@email-hub/ui/components/ui/badge";
import type { AgentMode } from "@/types/chat";
import type { ChatSession } from "@/types/chat-history";

const AGENT_LABELS: Record<AgentMode, string> = {
  chat: "Chat",
  scaffolder: "Scaffolder",
  dark_mode: "Dark Mode",
  content: "Content",
  outlook_fixer: "Outlook Fixer",
  accessibility: "Accessibility",
  personalisation: "Personalize",
  code_reviewer: "Reviewer",
  knowledge: "Knowledge",
  innovation: "Innovator",
};

interface SessionCardProps {
  session: ChatSession;
  onRestore: (session: ChatSession) => void;
  onDelete: (sessionId: string) => void;
}

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function SessionCard({ session, onRestore, onDelete }: SessionCardProps) {
  const timeAgo = formatRelativeTime(session.updatedAt);
  const label = AGENT_LABELS[session.agent] ?? session.agent;

  return (
    <div className="group rounded-lg border border-border bg-card p-3 transition-colors hover:border-border-accent">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
              {label}
            </Badge>
            <span className="text-[11px] text-muted-foreground">{timeAgo}</span>
          </div>

          <p className="mt-1.5 line-clamp-2 text-xs text-foreground">
            {session.preview}
          </p>

          <p className="mt-1 text-[11px] text-muted-foreground">
            {`${session.messageCount} messages`}
          </p>
        </div>

        <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => onRestore(session)}
            title={"Restore conversation"}
          >
            <RotateCcw className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
            onClick={() => onDelete(session.id)}
            title={"Delete session"}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
