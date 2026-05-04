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
      className="border-default bg-input text-foreground placeholder:text-muted-foreground focus:ring-interactive w-full resize-y rounded border px-2 py-1.5 font-mono text-xs focus:ring-1 focus:outline-none"
      placeholder={"<p>Enter HTML content...</p>"}
    />
  );
}
