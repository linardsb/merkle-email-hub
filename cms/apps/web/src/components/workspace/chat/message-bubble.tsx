"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { Bot, Check, Copy, Loader2, User } from "lucide-react";
import { Button } from "@email-hub/ui/components/ui/button";
import type { ChatMessage } from "@/types/chat";

/** Regex to split content into text and fenced code blocks. */
const CODE_BLOCK_RE = /```(\w*)\n([\s\S]*?)```/g;

interface CodeBlockProps {
  language: string;
  code: string;
  onApply?: () => void;
  showApply: boolean;
}

function CodeBlock({ language, code, onApply, showApply }: CodeBlockProps) {
  const t = useTranslations("workspace");
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  return (
    <div className="my-2 overflow-hidden rounded-md border border-border">
      <div className="flex items-center justify-between bg-muted px-3 py-1.5">
        <span className="text-xs text-muted-foreground">
          {language || "code"}
        </span>
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="mr-1 h-3 w-3" />
            ) : (
              <Copy className="mr-1 h-3 w-3" />
            )}
            {t("chatCopyCode")}
          </Button>
          {showApply && onApply && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-primary"
              onClick={onApply}
            >
              {t("chatApplyToEditor")}
            </Button>
          )}
        </div>
      </div>
      <pre className="overflow-x-auto bg-muted/50 p-3 text-xs">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function looksLikeHtml(code: string): boolean {
  const patterns = ["<!doctype", "<html", "<extends", "<table", "<div", "<td"];
  const lower = code.toLowerCase();
  return patterns.some((p) => lower.includes(p));
}

interface ParsedSegment {
  type: "text" | "code";
  content: string;
  language?: string;
}

function parseContent(content: string): ParsedSegment[] {
  const segments: ParsedSegment[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(CODE_BLOCK_RE)) {
    const matchIndex = match.index ?? 0;
    if (matchIndex > lastIndex) {
      segments.push({ type: "text", content: content.slice(lastIndex, matchIndex) });
    }
    segments.push({
      type: "code",
      content: match[2] ?? "",
      language: match[1] ?? "",
    });
    lastIndex = matchIndex + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({ type: "text", content: content.slice(lastIndex) });
  }

  return segments;
}

interface MessageBubbleProps {
  message: ChatMessage;
  onApplyHtml: (html: string) => void;
}

export function MessageBubble({ message, onApplyHtml }: MessageBubbleProps) {
  const t = useTranslations("workspace");

  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Assistant message
  if (message.isStreaming && !message.content) {
    return (
      <div className="flex gap-2">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Bot className="h-4 w-4 text-primary" />
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("chatThinking")}
        </div>
      </div>
    );
  }

  const segments = parseContent(message.content);

  return (
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1 text-sm">
        {segments.map((seg, i) =>
          seg.type === "code" ? (
            <CodeBlock
              key={i}
              language={seg.language ?? ""}
              code={seg.content}
              showApply={looksLikeHtml(seg.content)}
              onApply={() => onApplyHtml(seg.content)}
            />
          ) : (
            <p key={i} className="whitespace-pre-wrap text-foreground">
              {seg.content}
            </p>
          )
        )}
        {message.isStreaming && message.content && (
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-primary" />
        )}
      </div>
    </div>
  );
}
