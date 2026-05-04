"use client";

import type { AssignBlock } from "@/types/liquid-builder";

interface BlockAssignProps {
  block: AssignBlock;
  onUpdate: (updates: Partial<AssignBlock>) => void;
}

export function BlockAssign({ block, onUpdate }: BlockAssignProps) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={block.name}
        onChange={(e) => onUpdate({ name: e.target.value })}
        className="border-default bg-input text-foreground focus:ring-interactive w-28 rounded border px-2 py-1 font-mono text-xs focus:ring-1 focus:outline-none"
        placeholder="variable"
      />
      <span className="text-muted-foreground text-xs">=</span>
      <input
        type="text"
        value={block.expression}
        onChange={(e) => onUpdate({ expression: e.target.value })}
        className="border-default bg-input text-foreground focus:ring-interactive flex-1 rounded border px-2 py-1 font-mono text-xs focus:ring-1 focus:outline-none"
        placeholder={"'value' or expression"}
      />
    </div>
  );
}
