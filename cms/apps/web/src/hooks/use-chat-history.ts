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
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions(projectId));
  // Sync state → localStorage
  useEffect(() => {
    persistSessions(projectId, sessions);
  }, [projectId, sessions]);

  // Reload if projectId changes
  useEffect(() => {
    setSessions(loadSessions(projectId));
  }, [projectId]);

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
    [projectId],
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
