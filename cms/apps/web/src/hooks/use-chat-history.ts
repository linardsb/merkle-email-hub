"use client";

import { useCallback, useEffect, useState } from "react";
import type { ChatSession } from "@/types/chat-history";
import type { AgentMode, ChatMessage } from "@/types/chat";

const MAX_SESSIONS = 20;
const STORAGE_PREFIX = "chat-history-";

function getStorageKey(projectId: string): string {
  return `${STORAGE_PREFIX}${projectId}`;
}

function loadSessions(projectId: string): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(getStorageKey(projectId));
    return raw ? (JSON.parse(raw) as ChatSession[]) : [];
  } catch {
    return [];
  }
}

function persistSessions(projectId: string, sessions: ChatSession[]): void {
  try {
    localStorage.setItem(getStorageKey(projectId), JSON.stringify(sessions));
  } catch {
    // localStorage full — silently fail
  }
}

export function useChatHistory(projectId: string) {
  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    loadSessions(projectId)
  );
  const [seeded, setSeeded] = useState(false);

  // Sync state → localStorage
  useEffect(() => {
    persistSessions(projectId, sessions);
  }, [projectId, sessions]);

  // Reload if projectId changes
  useEffect(() => {
    setSessions(loadSessions(projectId));
    setSeeded(false);
  }, [projectId]);

  // Demo mode: seed history on first load if empty
  useEffect(() => {
    if (seeded) return;
    if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") return;

    const existing = loadSessions(projectId);
    if (existing.length > 0) {
      setSeeded(true);
      return;
    }

    import("@/lib/demo/chat-responses")
      .then(({ DEMO_CHAT_HISTORY }) => {
        if (DEMO_CHAT_HISTORY) {
          const projectSessions = DEMO_CHAT_HISTORY.filter(
            (s) => s.projectId === projectId
          );
          if (projectSessions.length > 0) {
            setSessions(projectSessions);
          }
        }
      })
      .catch(() => {
        // demo data unavailable — fine
      })
      .finally(() => setSeeded(true));
  }, [projectId, seeded]);

  const saveSession = useCallback(
    (messages: ChatMessage[], agent: AgentMode) => {
      if (messages.length === 0) return;

      const firstUserMsg = messages.find((m) => m.role === "user");
      const firstMsg = messages[0]!;
      const preview = firstUserMsg
        ? firstUserMsg.content.slice(0, 100)
        : firstMsg.content.slice(0, 100);

      const session: ChatSession = {
        id: `session-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        projectId,
        agent,
        messages,
        createdAt: firstMsg.timestamp,
        updatedAt: messages[messages.length - 1]!.timestamp,
        messageCount: messages.length,
        preview,
      };

      setSessions((prev) => {
        const updated = [session, ...prev];
        return updated.slice(0, MAX_SESSIONS);
      });
    },
    [projectId]
  );

  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
  }, []);

  const clearAllSessions = useCallback(() => {
    setSessions([]);
  }, []);

  return {
    sessions,
    saveSession,
    deleteSession,
    clearAllSessions,
  };
}
