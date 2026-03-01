"use client";

import { useCallback, useRef, useState } from "react";
import { authFetch, LONG_TIMEOUT_MS } from "@/lib/auth-fetch";
import type {
  AgentMode,
  ChatMessage,
  ChatStatus,
  SSEChunk,
  UseChatReturn,
} from "@/types/chat";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

function makeId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function buildUrl(agent: AgentMode): string {
  if (agent === "scaffolder") {
    return `${API_BASE}/api/v1/agents/scaffolder/generate`;
  }
  return `${API_BASE}/v1/chat/completions`;
}

function buildBody(
  content: string,
  agent: AgentMode,
  history: ChatMessage[]
): string {
  if (agent === "scaffolder") {
    return JSON.stringify({ brief: content, stream: true });
  }

  // Build message history for chat completions (last 20 messages)
  const recent = history
    .filter((m) => !m.isStreaming)
    .slice(-19)
    .map((m) => ({ role: m.role, content: m.content }));

  recent.push({ role: "user" as const, content });

  return JSON.stringify({ messages: recent, stream: true });
}

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStatus("idle");
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
  }, []);

  const sendMessage = useCallback(
    (content: string, agent: AgentMode) => {
      if (!content.trim() || status === "streaming") return;

      const userMsg: ChatMessage = {
        id: makeId(),
        role: "user",
        content: content.trim(),
        timestamp: Date.now(),
        agent,
        isStreaming: false,
      };

      const assistantId = makeId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        agent,
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStatus("streaming");
      setError(null);

      const controller = new AbortController();
      abortRef.current = controller;

      const url = buildUrl(agent);
      const body = buildBody(content, agent, messages);

      // Demo mode: simulate streaming from canned responses
      if (IS_DEMO) {
        (async () => {
          const { DEMO_CHAT_RESPONSES } = await import(
            "@/lib/demo/chat-responses"
          );
          const fullText = DEMO_CHAT_RESPONSES[agent] || DEMO_CHAT_RESPONSES.chat;
          const words = fullText.split(/(\s+)/);
          let accumulated = "";

          for (let i = 0; i < words.length; i++) {
            accumulated += words[i];
            const snapshot = accumulated;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: snapshot } : m,
              ),
            );
            // ~30ms per token for realistic typing feel
            await new Promise((r) => setTimeout(r, 15 + Math.random() * 30));
          }

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m,
            ),
          );
          setStatus("idle");
          abortRef.current = null;
        })();
        return;
      }

      (async () => {
        try {
          const res = await authFetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            signal: controller.signal,
            timeoutMs: LONG_TIMEOUT_MS,
          });

          if (!res.ok) {
            const text = await res.text().catch(() => "Request failed");
            throw new Error(text);
          }

          const reader = res.body?.getReader();
          if (!reader) throw new Error("No response body");

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            // Keep the last partial line in the buffer
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed || !trimmed.startsWith("data: ")) continue;

              const payload = trimmed.slice(6);
              if (payload === "[DONE]") break;

              try {
                const chunk: SSEChunk = JSON.parse(payload);
                const delta = chunk.choices?.[0]?.delta?.content;
                if (delta) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId
                        ? { ...m, content: m.content + delta }
                        : m
                    )
                  );
                }
              } catch {
                // Skip malformed chunks
              }
            }
          }

          // Mark streaming complete
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          );
          setStatus("idle");
        } catch (err) {
          if ((err as Error).name === "AbortError") return;

          // Remove empty assistant message on error
          setMessages((prev) =>
            prev.filter((m) => m.id !== assistantId || m.content.length > 0).map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          );
          const errMsg =
            err instanceof Error ? err.message : "Something went wrong";
          setError(errMsg);
          setStatus("error");
        } finally {
          abortRef.current = null;
        }
      })();
    },
    [status, messages]
  );

  const clearMessages = useCallback(() => {
    stopStreaming();
    setMessages([]);
    setError(null);
    setStatus("idle");
  }, [stopStreaming]);

  const replaceMessages = useCallback((newMessages: ChatMessage[]) => {
    setMessages(newMessages);
    setStatus("idle");
    setError(null);
  }, []);

  return { messages, status, error, sendMessage, stopStreaming, clearMessages, replaceMessages };
}
