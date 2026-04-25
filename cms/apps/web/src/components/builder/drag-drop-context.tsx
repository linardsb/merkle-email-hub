"use client";

import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  DragOverlay,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { useState, type ReactNode } from "react";

interface DragDropContextProps {
  items: string[];
  onReorder: (activeId: string, overId: string) => void;
  onExternalDrop?: (componentId: number, overId: string | null) => void;
  children: ReactNode;
}

export function DragDropContext({
  items,
  onReorder,
  onExternalDrop,
  children,
}: DragDropContextProps) {
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragId(null);
    const { active, over } = event;

    if (!over) return;

    const activeData = active.data.current;

    // External drop from palette
    if (activeData?.source === "palette") {
      onExternalDrop?.(activeData.componentId as number, over.id as string);
      return;
    }

    // Internal reorder
    if (active.id !== over.id) {
      onReorder(active.id as string, over.id as string);
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={(event) => setActiveDragId(event.active.id as string)}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={items} strategy={verticalListSortingStrategy}>
        {children}
      </SortableContext>
      <DragOverlay>
        {activeDragId ? (
          <div className="border-interactive bg-card text-foreground rounded border px-3 py-2 text-xs font-medium shadow-md">
            {"Moving section..."}
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
