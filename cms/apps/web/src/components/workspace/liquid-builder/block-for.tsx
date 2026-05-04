"use client";

import type { ForBlock } from "@/types/liquid-builder";

interface BlockForProps {
  block: ForBlock;
  onUpdate: (updates: Partial<ForBlock>) => void;
}

export function BlockFor({ block, onUpdate }: BlockForProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-xs font-medium">{"Variable"}</span>
        <input
          type="text"
          value={block.variable}
          onChange={(e) => onUpdate({ variable: e.target.value })}
          className="border-default bg-input text-foreground focus:ring-interactive w-24 rounded border px-2 py-1 font-mono text-xs focus:ring-1 focus:outline-none"
          placeholder="item"
        />
        <span className="text-muted-foreground text-xs">{"in"}</span>
        <input
          type="text"
          value={block.collection}
          onChange={(e) => onUpdate({ collection: e.target.value })}
          className="border-default bg-input text-foreground focus:ring-interactive flex-1 rounded border px-2 py-1 font-mono text-xs focus:ring-1 focus:outline-none"
          placeholder="products"
        />
      </div>
      {block.children.length > 0 && (
        <div className="border-interactive/30 border-l-2 pl-3">
          <p className="text-muted-foreground text-xs">{`${block.children.length} blocks`}</p>
        </div>
      )}
    </div>
  );
}
