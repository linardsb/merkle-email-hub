"use client";

import type { IfBlock } from "@/types/liquid-builder";

interface BlockIfProps {
  block: IfBlock;
  onUpdate: (updates: Partial<IfBlock>) => void;
}

export function BlockIf({ block, onUpdate }: BlockIfProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-xs font-medium">{"Condition"}</span>
        <input
          type="text"
          value={block.condition}
          onChange={(e) => onUpdate({ condition: e.target.value })}
          className="border-default bg-input text-foreground focus:ring-interactive flex-1 rounded border px-2 py-1 font-mono text-xs focus:ring-1 focus:outline-none"
          placeholder="subscriber.tier == 'gold'"
        />
      </div>
      {block.children.length > 0 && (
        <div className="border-success/30 border-l-2 pl-3">
          <span className="text-success text-[10px] tracking-wider uppercase">{"Then"}</span>
          <p className="text-muted-foreground mt-1 text-xs">{`${block.children.length} blocks`}</p>
        </div>
      )}
      {block.elseChildren.length > 0 && (
        <div className="border-warning/30 border-l-2 pl-3">
          <span className="text-warning text-[10px] tracking-wider uppercase">{"Else"}</span>
          <p className="text-muted-foreground mt-1 text-xs">{`${block.elseChildren.length} blocks`}</p>
        </div>
      )}
    </div>
  );
}
