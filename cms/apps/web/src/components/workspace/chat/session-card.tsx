"use client";

import { useTranslations } from "next-intl";
import { RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@email-hub/ui/components/ui/button";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { AGENT_LABEL_KEYS } from "@/types/chat";
import type { ChatSession } from "@/types/chat-history";

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
  const t = useTranslations("workspace");

  const timeAgo = formatRelativeTime(session.updatedAt);
  const labelKey = AGENT_LABEL_KEYS[session.agent];

  return (
    <div className="group rounded-lg border border-border bg-card p-3 transition-colors hover:border-border-accent">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
              {t(labelKey as Parameters<typeof t>[0])}
            </Badge>
            <span className="text-[11px] text-muted-foreground">{timeAgo}</span>
          </div>

          <p className="mt-1.5 line-clamp-2 text-xs text-foreground">
            {session.preview}
          </p>

          <p className="mt-1 text-[11px] text-muted-foreground">
            {t("historyMessageCount", { count: session.messageCount })}
          </p>
        </div>

        <div className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => onRestore(session)}
            title={t("historyRestore")}
          >
            <RotateCcw className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
            onClick={() => onDelete(session.id)}
            title={t("historyDelete")}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
