"use client";

import { useTranslations } from "next-intl";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import type { BlockTree, LiquidBlock } from "@/types/liquid-builder";
import { BlockNode } from "./block-node";

interface BlockCanvasProps {
  blocks: BlockTree;
  onMove: (activeId: string, overId: string) => void;
  onUpdate: (id: string, updates: Partial<LiquidBlock>) => void;
  onRemove: (id: string) => void;
}

export function BlockCanvas({ blocks, onMove, onUpdate, onRemove }: BlockCanvasProps) {
  const t = useTranslations("liquidBuilder");
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      onMove(active.id as string, over.id as string);
    }
  };

  if (blocks.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">{t("canvasEmpty")}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={blocks.map((b) => b.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {blocks.map((block) => (
              <BlockNode
                key={block.id}
                block={block}
                onUpdate={onUpdate}
                onRemove={onRemove}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
