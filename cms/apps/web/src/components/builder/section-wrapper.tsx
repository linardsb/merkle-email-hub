"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Copy, Trash2 } from "../icons";
import DOMPurify from "dompurify";
import type { BuilderSection } from "@/types/visual-builder";

interface SectionWrapperProps {
  section: BuilderSection;
  isSelected: boolean;
  onSelect: () => void;
  onRemove: () => void;
  onDuplicate: () => void;
}

export function SectionWrapper({
  section,
  isSelected,
  onSelect,
  onRemove,
  onDuplicate,
}: SectionWrapperProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: section.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative cursor-pointer ${
        isSelected ? "ring-interactive ring-2" : "hover:ring-border ring-1 ring-transparent"
      }`}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Section: ${section.componentName}`}
      aria-selected={isSelected}
    >
      {/* Section label */}
      <div
        className={`bg-card text-muted-foreground absolute -top-5 left-2 z-10 rounded-t px-1.5 py-0.5 text-[10px] ${
          isSelected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        } transition-opacity`}
      >
        {section.componentName}
      </div>

      {/* Action toolbar */}
      {isSelected && (
        <div className="bg-card border-border absolute -top-3 right-2 z-10 flex gap-0.5 rounded border shadow-sm">
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground cursor-grab p-1 active:cursor-grabbing"
            aria-label="Drag to reorder"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground p-1"
            onClick={(e) => {
              e.stopPropagation();
              onDuplicate();
            }}
            aria-label="Duplicate section"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="text-muted-foreground hover:text-destructive p-1"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            aria-label="Remove section"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Section content */}
      <div
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(section.html, {
            ADD_TAGS: ["center"],
            ADD_ATTR: [
              "role",
              "cellpadding",
              "cellspacing",
              "width",
              "height",
              "bgcolor",
              "align",
              "valign",
              "border",
            ],
          }),
        }}
      />
    </div>
  );
}
