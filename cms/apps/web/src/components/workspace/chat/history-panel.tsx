"use client";

import { useTranslations } from "next-intl";
import { History, Trash2 } from "lucide-react";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import { SessionCard } from "./session-card";
import type { ChatSession } from "@/types/chat-history";

interface HistoryPanelProps {
  sessions: ChatSession[];
  onRestore: (session: ChatSession) => void;
  onDelete: (sessionId: string) => void;
  onClearAll: () => void;
}

export function HistoryPanel({
  sessions,
  onRestore,
  onDelete,
  onClearAll,
}: HistoryPanelProps) {
  const t = useTranslations("workspace");

  if (sessions.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-4">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <History className="h-5 w-5" />
          <p className="text-sm">{t("historyEmpty")}</p>
          <p className="text-xs">{t("historyEmptyDescription")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-xs text-muted-foreground">
          {t("historyCount", { count: sessions.length })}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-2 text-[11px] text-muted-foreground"
          onClick={onClearAll}
        >
          <Trash2 className="h-3 w-3" />
          {t("historyClearAll")}
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
