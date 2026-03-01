"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import {
  MessageSquare,
  Wand2,
  Moon,
  PenTool,
  Trash2,
} from "lucide-react";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import { Badge } from "@merkle-email-hub/ui/components/ui/badge";
import { useChat } from "@/hooks/use-chat";
import { MessageList } from "./chat/message-list";
import { ChatInput } from "./chat/chat-input";
import type { AgentMode } from "@/types/chat";

interface AgentOption {
  id: AgentMode;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  enabled: boolean;
}

const AGENTS: AgentOption[] = [
  { id: "chat", labelKey: "chatAgentChat", icon: MessageSquare, enabled: true },
  { id: "scaffolder", labelKey: "chatAgentScaffolder", icon: Wand2, enabled: true },
  { id: "dark_mode", labelKey: "chatAgentDarkMode", icon: Moon, enabled: false },
  { id: "content", labelKey: "chatAgentContent", icon: PenTool, enabled: false },
];

interface ChatPanelProps {
  onApplyToEditor?: (html: string) => void;
}

export function ChatPanel({ onApplyToEditor }: ChatPanelProps) {
  const t = useTranslations("workspace");
  const [agent, setAgent] = useState<AgentMode>("chat");
  const { messages, status, error, sendMessage, stopStreaming, clearMessages } =
    useChat();

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content, agent);
    },
    [sendMessage, agent]
  );

  const handleApplyHtml = useCallback(
    (html: string) => {
      onApplyToEditor?.(html);
    },
    [onApplyToEditor]
  );

  const placeholder =
    agent === "scaffolder"
      ? t("chatScaffolderPlaceholder")
      : t("chatInputPlaceholder");

  const emptyText =
    agent === "scaffolder" ? t("chatScaffolderEmpty") : t("chatEmpty");

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header: Agent selector + Clear */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <div className="flex flex-1 items-center gap-1">
          {AGENTS.map((opt) => {
            const Icon = opt.icon;
            const isActive = agent === opt.id;

            return (
              <Button
                key={opt.id}
                variant="ghost"
                size="sm"
                disabled={!opt.enabled}
                className={`h-7 gap-1.5 px-2.5 text-xs ${isActive ? "bg-accent text-accent-foreground" : ""}`}
                onClick={() => setAgent(opt.id)}
              >
                <Icon className="h-3.5 w-3.5" />
                {t(opt.labelKey)}
                {!opt.enabled && (
                  <Badge
                    variant="secondary"
                    className="ml-0.5 px-1 py-0 text-[10px]"
                  >
                    {t("chatComingSoon")}
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>

        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 px-2 text-xs text-muted-foreground"
            onClick={clearMessages}
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t("chatClear")}
          </Button>
        )}
      </div>

      {/* Message area */}
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center p-4 text-center">
          <MessageSquare className="h-8 w-8 text-muted-foreground" />
          <p className="mt-2 max-w-xs text-sm text-muted-foreground">
            {emptyText}
          </p>
        </div>
      ) : (
        <MessageList messages={messages} onApplyHtml={handleApplyHtml} />
      )}

      {/* Error banner */}
      {status === "error" && error && (
        <div className="border-t border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {t("chatError")}
        </div>
      )}

      {/* Input */}
      <ChatInput
        onSend={handleSend}
        onStop={stopStreaming}
        status={status}
        placeholder={placeholder}
      />
    </div>
  );
}
