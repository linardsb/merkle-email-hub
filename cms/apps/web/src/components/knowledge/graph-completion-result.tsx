"use client";

import { MessageSquare } from "lucide-react";

interface GraphCompletionResultProps {
  content: string;
  query: string;
}

export function GraphCompletionResult({ content, query }: GraphCompletionResultProps) {
  return (
    <div className="animate-fade-in space-y-3">
      {/* Question echo */}
      <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4">
        <MessageSquare className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
        <p className="text-sm italic text-muted-foreground">{query}</p>
      </div>

      {/* Answer */}
      <div className="rounded-lg border border-border bg-card p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          {"Answer from knowledge graph"}
        </p>
        <div className="text-sm text-foreground">
          <p className="whitespace-pre-line">{content}</p>
        </div>
      </div>
    </div>
  );
}
