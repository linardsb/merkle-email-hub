"use client";

import { MessageSquare } from "../icons";

interface GraphCompletionResultProps {
  content: string;
  query: string;
}

export function GraphCompletionResult({ content, query }: GraphCompletionResultProps) {
  return (
    <div className="animate-fade-in space-y-3">
      {/* Question echo */}
      <div className="border-border bg-muted/50 flex items-start gap-3 rounded-lg border p-4">
        <MessageSquare className="text-muted-foreground mt-0.5 h-5 w-5 shrink-0" />
        <p className="text-muted-foreground text-sm italic">{query}</p>
      </div>

      {/* Answer */}
      <div className="border-border bg-card rounded-lg border p-4">
        <p className="text-muted-foreground mb-2 text-xs font-semibold uppercase tracking-wider">
          {"Answer from knowledge graph"}
        </p>
        <div className="text-foreground text-sm">
          <p className="whitespace-pre-line">{content}</p>
        </div>
      </div>
    </div>
  );
}
