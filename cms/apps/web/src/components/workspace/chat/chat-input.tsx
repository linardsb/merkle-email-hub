"use client";

import { useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Send, Square } from "lucide-react";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import type { ChatStatus } from "@/types/chat";

interface ChatInputProps {
  onSend: (content: string) => void;
  onStop: () => void;
  status: ChatStatus;
  placeholder?: string;
}

export function ChatInput({ onSend, onStop, status, placeholder }: ChatInputProps) {
  const t = useTranslations("workspace");
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
    [isStreaming, handleSend]
  );

  return (
    <div className="flex items-end gap-2 border-t border-border p-3">
      <textarea
        ref={textareaRef}
        className="flex-1 resize-none rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        placeholder={placeholder ?? t("chatInputPlaceholder")}
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
          aria-label={t("chatStop")}
        >
          <Square className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground"
          onClick={handleSend}
          aria-label={t("chatSend")}
        >
          <Send className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
