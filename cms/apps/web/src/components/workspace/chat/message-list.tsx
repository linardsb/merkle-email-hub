"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import type { ChatMessage } from "@/types/chat";

interface MessageListProps {
  messages: ChatMessage[];
  onApplyHtml: (html: string) => void;
}

export function MessageList({ messages, onApplyHtml }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-4 p-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onApplyHtml={onApplyHtml}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
