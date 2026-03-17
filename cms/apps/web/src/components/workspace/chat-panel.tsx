"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  MessageSquare,
  Trash2,
  History,
  Zap,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { Button } from "@email-hub/ui/components/ui/button";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { Checkbox } from "@email-hub/ui/components/ui/checkbox";
import { useChat } from "@/hooks/use-chat";
import { useChatHistory } from "@/hooks/use-chat-history";
import { MessageList } from "./chat/message-list";
import { ChatInput } from "./chat/chat-input";
import { HistoryPanel } from "./chat/history-panel";
import { AgentSelectorDropdown } from "./chat/agent-selector-dropdown";
import type { AgentMode } from "@/types/chat";
import type { ChatPanelTab, ChatSession } from "@/types/chat-history";

interface ChatPanelProps {
  projectId?: string;
  onApplyToEditor?: (html: string) => void;
  initialAgent?: AgentMode;
  editorContent?: string;
}

export function ChatPanel({ projectId = "default", onApplyToEditor, initialAgent, editorContent }: ChatPanelProps) {
  const t = useTranslations("workspace");
  const [agent, setAgent] = useState<AgentMode>(initialAgent ?? "chat");
  const [activeTab, setActiveTab] = useState<ChatPanelTab>("chat");
  const [blueprintMode, setBlueprintMode] = useState(false);
  const [includeHtml, setIncludeHtml] = useState(false);
  const {
    messages, status, error,
    sendMessage, sendBlueprintRun, blueprintRunning,
    stopStreaming, clearMessages, replaceMessages,
  } = useChat(projectId);
  const {
    sessions, saveSession, deleteSession, clearAllSessions,
  } = useChatHistory(projectId);

  const handleSend = useCallback(
    (content: string) => {
      if (blueprintMode) {
        sendBlueprintRun(content, {
          includeHtml,
          currentHtml: editorContent,
          projectId,
        });
      } else {
        sendMessage(content, agent);
      }
    },
    [blueprintMode, sendMessage, sendBlueprintRun, agent, includeHtml, editorContent, projectId]
  );

  const handleApplyHtml = useCallback(
    (html: string) => {
      onApplyToEditor?.(html);
    },
    [onApplyToEditor]
  );

  // Save current conversation before clearing
  const handleClear = useCallback(() => {
    if (messages.length > 0) {
      saveSession(messages, agent);
    }
    clearMessages();
  }, [messages, agent, saveSession, clearMessages]);

  // Restore a past session
  const handleRestore = useCallback(
    (session: ChatSession) => {
      if (messages.length > 0) {
        saveSession(messages, agent);
      }
      replaceMessages(session.messages);
      setAgent(session.agent);
      setActiveTab("chat");
    },
    [messages, agent, saveSession, replaceMessages]
  );

  // Auto-save on page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (messages.length > 0) {
        saveSession(messages, agent);
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [messages, agent, saveSession]);

  const emptyKey = `chatEmpty_${agent}` as const;
  const placeholderKey = `chatPlaceholder_${agent}` as const;
  const emptyText = t.has(emptyKey) ? t(emptyKey) : t("chatEmpty");
  const placeholder = t.has(placeholderKey) ? t(placeholderKey) : t("chatInputPlaceholder");

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Top-level tabs: Chat | History */}
      <div className="flex gap-1 border-b border-border bg-muted/50 px-2 pt-2" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "chat"}
          onClick={() => setActiveTab("chat")}
          className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-t-md px-4 py-2 text-sm font-medium transition-all ${
            activeTab === "chat"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          {t("chatTab")}
          {messages.length > 0 && (
            <Badge variant="secondary" className="ml-0.5 px-1.5 py-0 text-[10px]">
              {messages.length}
            </Badge>
          )}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
          className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-t-md px-4 py-2 text-sm font-medium transition-all ${
            activeTab === "history"
              ? "border border-b-0 border-border bg-background text-foreground"
              : "border border-transparent text-muted-foreground hover:border-border/50 hover:bg-background/60 hover:text-foreground"
          }`}
        >
          <History className="h-4 w-4" />
          {t("historyTab")}
          {sessions.length > 0 && (
            <Badge variant="secondary" className="ml-0.5 px-1.5 py-0 text-[10px]">
              {sessions.length}
            </Badge>
          )}
        </button>
      </div>

      {/* Tab content */}
      {activeTab === "chat" ? (
        <>
          {/* Blueprint mode toggle + Agent selector / Blueprint label */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            {/* Toggle */}
            <button
              type="button"
              onClick={() => setBlueprintMode((v) => !v)}
              className="flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors hover:bg-accent"
              title={t("blueprintChatToggleTitle")}
            >
              {blueprintMode ? (
                <ToggleRight className="h-4 w-4 text-primary" />
              ) : (
                <ToggleLeft className="h-4 w-4 text-muted-foreground" />
              )}
              <Zap className={`h-3 w-3 ${blueprintMode ? "text-primary" : "text-muted-foreground"}`} />
            </button>

            {blueprintMode ? (
              /* Blueprint mode: label + include HTML checkbox */
              <div className="flex flex-1 items-center gap-3">
                <span className="text-xs font-medium text-primary">
                  {t("blueprintChatModeLabel")}
                </span>
                <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Checkbox
                    checked={includeHtml}
                    onCheckedChange={(v) => setIncludeHtml(v === true)}
                    className="h-3.5 w-3.5"
                  />
                  {t("blueprintChatIncludeHtml")}
                </label>
              </div>
            ) : (
              /* Agent mode: dropdown selector */
              <div className="flex flex-1 items-center">
                <AgentSelectorDropdown agent={agent} onSelect={setAgent} />
              </div>
            )}

            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 shrink-0 gap-1 px-2 text-xs text-muted-foreground"
                onClick={handleClear}
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
                {blueprintMode ? (
                  <Zap className="h-5 w-5 shrink-0" />
                ) : (
                  <MessageSquare className="h-5 w-5 shrink-0" />
                )}
                <p className="text-sm">
                  {blueprintMode ? t("blueprintChatEmpty") : emptyText}
                </p>
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
            status={blueprintRunning ? "streaming" : status}
            placeholder={blueprintMode ? t("blueprintChatPlaceholder") : placeholder}
          />
        </>
      ) : (
        <HistoryPanel
          sessions={sessions}
          onRestore={handleRestore}
          onDelete={deleteSession}
          onClearAll={clearAllSessions}
        />
      )}
    </div>
  );
}
