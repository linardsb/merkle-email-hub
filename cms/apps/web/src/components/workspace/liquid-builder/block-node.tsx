"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, X, GitBranch, Repeat, Variable, Braces, Code } from "../../icons";
import type { LiquidBlock } from "@/types/liquid-builder";
import { BlockIf } from "./block-if";
import { BlockFor } from "./block-for";
import { BlockAssign } from "./block-assign";
import { BlockOutput } from "./block-output";
import { BlockRaw } from "./block-raw";

const BLOCK_TYPE_LABELS: Record<string, string> = {
  if: "If",
  for: "For Loop",
  assign: "Assign",
  output: "Output",
  raw: "Raw HTML",
};

const BLOCK_ICONS: Record<LiquidBlock["type"], React.ReactNode> = {
  if: <GitBranch className="h-3.5 w-3.5" />,
  for: <Repeat className="h-3.5 w-3.5" />,
  assign: <Variable className="h-3.5 w-3.5" />,
  output: <Braces className="h-3.5 w-3.5" />,
  raw: <Code className="h-3.5 w-3.5" />,
};

const BLOCK_COLORS: Record<LiquidBlock["type"], string> = {
  if: "border-l-success",
  for: "border-l-interactive",
  assign: "border-l-warning",
  output: "border-l-accent-foreground",
  raw: "border-l-muted",
};

interface BlockNodeProps {
  block: LiquidBlock;
  onUpdate: (id: string, updates: Partial<LiquidBlock>) => void;
  onRemove: (id: string) => void;
}

export function BlockNode({ block, onUpdate, onRemove }: BlockNodeProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: block.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const handleUpdate = (updates: Partial<LiquidBlock>) => {
    onUpdate(block.id, updates);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-md border border-default ${BLOCK_COLORS[block.type]} border-l-4 bg-card`}
    >
      <div className="flex items-center gap-2 border-b border-default px-2 py-1.5">
        <button
          type="button"
          className="cursor-grab text-muted-foreground hover:text-foreground active:cursor-grabbing"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-3.5 w-3.5" />
        </button>
        {BLOCK_ICONS[block.type]}
        <span className="flex-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {BLOCK_TYPE_LABELS[block.type] ?? block.type}
        </span>
        <button
          type="button"
          onClick={() => onRemove(block.id)}
          className="rounded p-0.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="p-2">
        {block.type === "if" && <BlockIf block={block} onUpdate={handleUpdate} />}
        {block.type === "for" && <BlockFor block={block} onUpdate={handleUpdate} />}
        {block.type === "assign" && <BlockAssign block={block} onUpdate={handleUpdate} />}
        {block.type === "output" && <BlockOutput block={block} onUpdate={handleUpdate} />}
        {block.type === "raw" && <BlockRaw block={block} onUpdate={handleUpdate} />}
      </div>
    </div>
  );
}
