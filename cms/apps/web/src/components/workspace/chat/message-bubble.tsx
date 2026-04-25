"use client";

import { useCallback, useState } from "react";
import { Bot, Check, Copy, Loader2, User } from "../../icons";
import { Button } from "@email-hub/ui/components/ui/button";
import type { ChatMessage } from "@/types/chat";
import { ConfidenceIndicator } from "./confidence-indicator";
import { BlueprintResultCard } from "./blueprint-result-card";

/** Regex to split content into text and fenced code blocks. */
const CODE_BLOCK_RE = /```(\w*)\n([\s\S]*?)```/g;

interface CodeBlockProps {
  language: string;
  code: string;
  onApply?: () => void;
  showApply: boolean;
}

function CodeBlock({ language, code, onApply, showApply }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  return (
    <div className="border-border my-2 overflow-hidden rounded-md border">
      <div className="bg-muted flex items-center justify-between px-3 py-1.5">
        <span className="text-muted-foreground text-xs">{language || "code"}</span>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={handleCopy}>
            {copied ? <Check className="mr-1 h-3 w-3" /> : <Copy className="mr-1 h-3 w-3" />}
            {"Copy"}
          </Button>
          {showApply && onApply && (
            <Button
              variant="ghost"
              size="sm"
              className="text-primary h-6 px-2 text-xs"
              onClick={onApply}
            >
              {"Apply"}
            </Button>
          )}
        </div>
      </div>
      <pre className="bg-muted/50 overflow-x-auto p-3 text-xs">
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
  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="bg-primary text-primary-foreground max-w-[80%] rounded-lg px-3 py-2 text-sm">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="bg-muted flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
          <User className="text-muted-foreground h-4 w-4" />
        </div>
      </div>
    );
  }

  // Assistant message
  if (message.isStreaming && !message.content) {
    return (
      <div className="flex gap-2">
        <div className="bg-primary/10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
          <Bot className="text-primary h-4 w-4" />
        </div>
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {"Thinking..."}
        </div>
      </div>
    );
  }

  const segments = parseContent(message.content);

  return (
    <div className="flex gap-2">
      <div className="bg-primary/10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
        <Bot className="text-primary h-4 w-4" />
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
            <p key={i} className="text-foreground whitespace-pre-wrap">
              {seg.content}
            </p>
          ),
        )}
        {/* Blueprint pipeline result */}
        {!message.isStreaming && message.blueprintResult && (
          <BlueprintResultCard result={message.blueprintResult} onApplyHtml={onApplyHtml} />
        )}
        {message.isStreaming && message.content && (
          <span className="bg-primary ml-0.5 inline-block h-4 w-1.5 animate-pulse" />
        )}
        {!message.isStreaming && message.confidence != null && (
          <ConfidenceIndicator confidence={message.confidence} />
        )}
      </div>
    </div>
  );
}
