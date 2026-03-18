"use client";

import { useCallback, useEffect, useState } from "react";
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

  const EMPTY_TEXT: Record<string, string> = {
    chat: "Ask a question about email development, HTML, CSS, or Maizzle.",
    scaffolder: "Describe your email and the Scaffolder will generate a template.",
    dark_mode: "Paste your HTML and the Dark Mode agent will optimize it.",
    content: "Describe your content needs and the Content agent will help.",
    outlook_fixer: "Paste your HTML and the Outlook Fixer will patch compatibility issues.",
    accessibility: "Paste your HTML and the Accessibility agent will audit it.",
    personalisation: "Describe your personalisation needs.",
    code_reviewer: "Paste your HTML for a code review.",
    knowledge: "Ask about email development best practices.",
    innovation: "Explore new email techniques and innovations.",
  };
  const PLACEHOLDER_TEXT: Record<string, string> = {
    chat: "Ask the AI assistant...",
    scaffolder: "Describe the email you want to build...",
    dark_mode: "Paste HTML to optimize for dark mode...",
    content: "Describe your content needs...",
    outlook_fixer: "Paste HTML to fix for Outlook...",
    accessibility: "Paste HTML to audit for accessibility...",
    personalisation: "Describe personalisation requirements...",
    code_reviewer: "Paste HTML for code review...",
    knowledge: "Ask about email best practices...",
    innovation: "Explore new email techniques...",
  };
  const emptyText = EMPTY_TEXT[agent] ?? "Ask a question about email development, HTML, CSS, or Maizzle.";
  const placeholder = PLACEHOLDER_TEXT[agent] ?? "Ask the AI assistant...";

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
          {"Chat"}
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
          {"History"}
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
              title={"Toggle Blueprint Mode"}
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
                  {"Blueprint Pipeline"}
                </span>
                <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Checkbox
                    checked={includeHtml}
                    onCheckedChange={(v) => setIncludeHtml(v === true)}
                    className="h-3.5 w-3.5"
                  />
                  {"Include current HTML"}
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
                {"Clear"}
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
                  {blueprintMode ? "Blueprint Mode — describe a campaign brief and the full agent pipeline will execute automatically" : emptyText}
                </p>
              </div>
            </div>
          ) : (
            <MessageList messages={messages} onApplyHtml={handleApplyHtml} />
          )}

          {/* Error banner */}
          {status === "error" && error && (
            <div className="border-t border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {"Something went wrong. Please try again."}
            </div>
          )}

          {/* Input */}
          <ChatInput
            onSend={handleSend}
            onStop={stopStreaming}
            status={blueprintRunning ? "streaming" : status}
            placeholder={blueprintMode ? "Describe your email campaign brief..." : placeholder}
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
