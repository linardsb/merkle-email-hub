"use client";

import { useCallback, useRef } from "react";
import { Send, Square } from "../../icons";
import { Button } from "@email-hub/ui/components/ui/button";
import type { ChatStatus } from "@/types/chat";

interface ChatInputProps {
  onSend: (content: string) => void;
  onStop: () => void;
  status: ChatStatus;
  placeholder?: string;
}

export function ChatInput({ onSend, onStop, status, placeholder }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isStreaming = status === "streaming";

  const handleInput = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  const handleSend = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    const value = el.value.trim();
    if (!value) return;
    onSend(value);
    el.value = "";
    el.style.height = "auto";
  }, [onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!isStreaming) handleSend();
      }
    },
    [isStreaming, handleSend],
  );

  return (
    <div className="border-border flex items-end gap-2 border-t p-3">
      <textarea
        ref={textareaRef}
        className="border-input placeholder:text-muted-foreground focus-visible:ring-ring flex-1 resize-none rounded-md border bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
        placeholder={placeholder ?? "Ask the AI assistant..."}
        rows={1}
        disabled={isStreaming}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
      />
      {isStreaming ? (
        <Button
          variant="destructive"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={onStop}
          aria-label={"Stop generating"}
        >
          <Square className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground h-9 w-9 shrink-0"
          onClick={handleSend}
          aria-label={"Send message"}
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
