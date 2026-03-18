"use client";

import type { RawBlock } from "@/types/liquid-builder";

interface BlockRawProps {
  block: RawBlock;
  onUpdate: (updates: Partial<RawBlock>) => void;
}

export function BlockRaw({ block, onUpdate }: BlockRawProps) {
  return (
    <textarea
      value={block.content}
      onChange={(e) => onUpdate({ content: e.target.value })}
      rows={3}
      className="w-full resize-y rounded border border-default bg-input px-2 py-1.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-interactive"
      placeholder={"<p>Enter HTML content...</p>"}
    />
  );
}
