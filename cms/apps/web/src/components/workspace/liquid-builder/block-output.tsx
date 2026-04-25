"use client";

import type { OutputBlock } from "@/types/liquid-builder";

interface BlockOutputProps {
  block: OutputBlock;
  onUpdate: (updates: Partial<OutputBlock>) => void;
}

export function BlockOutput({ block, onUpdate }: BlockOutputProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground font-mono text-xs">{"{{"}</span>
      <input
        type="text"
        value={block.expression}
        onChange={(e) => onUpdate({ expression: e.target.value })}
        className="border-default bg-input text-foreground focus:ring-interactive flex-1 rounded border px-2 py-1 font-mono text-xs focus:outline-none focus:ring-1"
        placeholder={"subscriber.first_name"}
      />
      <span className="text-muted-foreground font-mono text-xs">{"}}"}</span>
    </div>
  );
}
