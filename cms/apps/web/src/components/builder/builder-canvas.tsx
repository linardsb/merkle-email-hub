"use client";

import { ArrowDown } from "lucide-react";
import { useDroppable } from "@dnd-kit/core";
import { SectionWrapper } from "./section-wrapper";
import type { BuilderSection } from "@/types/visual-builder";

interface DropZoneProps {
  id: string;
}

function DropZone({ id }: DropZoneProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={`mx-auto transition-all ${
        isOver
          ? "h-8 border-2 border-dashed border-interactive bg-interactive/10"
          : "h-1"
      }`}
      style={{ maxWidth: 600 }}
    />
  );
}

function EmptyDropZone() {
  const { setNodeRef, isOver } = useDroppable({ id: "drop-zone-0" });

  return (
    <div ref={setNodeRef} className="flex h-full items-center justify-center">
      <div
        className={`flex flex-col items-center gap-3 rounded-lg border-2 border-dashed p-8 text-muted-foreground transition-colors ${
          isOver
            ? "border-interactive bg-interactive/10"
            : "border-border"
        }`}
      >
        <ArrowDown className="h-8 w-8 opacity-40" />
        <p className="text-sm">
          {"Drag components here to start building"}
        </p>
      </div>
    </div>
  );
}

interface BuilderCanvasProps {
  sections: BuilderSection[];
  selectedSectionId: string | null;
  onSelect: (id: string | null) => void;
  onRemove: (id: string) => void;
  onDuplicate: (id: string) => void;
}

export function BuilderCanvas({
  sections,
  selectedSectionId,
  onSelect,
  onRemove,
  onDuplicate,
}: BuilderCanvasProps) {
  if (sections.length === 0) {
    return <EmptyDropZone />;
  }

  return (
    <div
      className="flex-1 overflow-y-auto p-4"
      onClick={() => onSelect(null)}
      onKeyDown={(e) => {
        if (e.key === "Escape") onSelect(null);
      }}
      role="presentation"
    >
      <div className="mx-auto" style={{ maxWidth: 600 }}>
        <DropZone id="drop-zone-0" />
        {sections.map((section, index) => (
          <div key={section.id}>
            <SectionWrapper
              section={section}
              isSelected={selectedSectionId === section.id}
              onSelect={() => onSelect(section.id)}
              onRemove={() => onRemove(section.id)}
              onDuplicate={() => onDuplicate(section.id)}
            />
            <DropZone id={`drop-zone-${index + 1}`} />
          </div>
        ))}
      </div>
    </div>
  );
}
