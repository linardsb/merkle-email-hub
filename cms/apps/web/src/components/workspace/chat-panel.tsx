"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import {
  MessageSquare,
  Wand2,
  Moon,
  PenTool,
  Trash2,
  Wrench,
  Eye,
  Users,
  FileSearch,
  BookOpen,
  Lightbulb,
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
  { id: "dark_mode", labelKey: "chatAgentDarkMode", icon: Moon, enabled: true },
  { id: "content", labelKey: "chatAgentContent", icon: PenTool, enabled: true },
  { id: "outlook_fixer", labelKey: "chatAgentOutlookFixer", icon: Wrench, enabled: true },
  { id: "accessibility", labelKey: "chatAgentAccessibility", icon: Eye, enabled: true },
  { id: "personalisation", labelKey: "chatAgentPersonalisation", icon: Users, enabled: true },
  { id: "code_reviewer", labelKey: "chatAgentCodeReviewer", icon: FileSearch, enabled: true },
  { id: "knowledge", labelKey: "chatAgentKnowledge", icon: BookOpen, enabled: true },
  { id: "innovation", labelKey: "chatAgentInnovation", icon: Lightbulb, enabled: true },
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

  const emptyKey = `chatEmpty_${agent}` as const;
  const placeholderKey = `chatPlaceholder_${agent}` as const;
  // Each agent has its own empty-state description and input placeholder
  const emptyText = t.has(emptyKey) ? t(emptyKey) : t("chatEmpty");
  const placeholder = t.has(placeholderKey) ? t(placeholderKey) : t("chatInputPlaceholder");

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header: Agent selector + Clear */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <div className="flex flex-1 items-center gap-1 overflow-x-auto scrollbar-none">
          {AGENTS.map((opt) => {
            const Icon = opt.icon;
            const isActive = agent === opt.id;

            return (
              <Button
                key={opt.id}
                variant="ghost"
                size="sm"
                disabled={!opt.enabled}
                className={`h-7 shrink-0 gap-1.5 px-2 text-xs ${isActive ? "bg-accent text-accent-foreground" : ""}`}
                onClick={() => setAgent(opt.id)}
              >
                <Icon className="h-3.5 w-3.5" />
                {t(opt.labelKey)}
              </Button>
            );
          })}
        </div>

        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 shrink-0 gap-1 px-2 text-xs text-muted-foreground"
            onClick={clearMessages}
          >
            <Trash2 className="h-3.5 w-3.5" />
            {t("chatClear")}
          </Button>
        )}
      </div>

      {/* Message area */}
      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center px-6 py-4">
          <div className="flex items-center gap-3 text-muted-foreground">
            <MessageSquare className="h-5 w-5 shrink-0" />
            <p className="text-sm">{emptyText}</p>
          </div>
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
