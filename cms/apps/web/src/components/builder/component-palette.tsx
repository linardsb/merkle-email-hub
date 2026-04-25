"use client";

import { useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import {
  Search,
  Layout,
  Type,
  MousePointerClick,
  MousePointer,
  Sparkles,
  Wrench,
  Puzzle,
} from "../icons";
import { useComponents } from "@/hooks/use-components";
import { SECTION_CATEGORIES, type SectionCategory } from "@/types/visual-builder";
import type { ComponentResponse } from "@email-hub/sdk";
import { CompatibilityBadge } from "@/components/components/compatibility-badge";

const CATEGORY_ICONS: Record<SectionCategory, typeof Layout> = {
  structure: Layout,
  content: Type,
  action: MousePointerClick,
  interactive: MousePointer,
  animation: Sparkles,
  utility: Wrench,
};

function PaletteCard({ component }: { component: ComponentResponse }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette-${component.id}`,
    data: { source: "palette", componentId: component.id, component },
  });

  const category = (component.category ?? "content") as SectionCategory;
  const Icon = CATEGORY_ICONS[category] ?? Puzzle;

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      className={`border-border bg-card hover:bg-accent flex cursor-grab items-center gap-2 rounded border p-2 text-sm transition-colors active:cursor-grabbing ${
        isDragging ? "opacity-50" : ""
      }`}
      role="button"
      tabIndex={0}
      aria-label={`Drag ${component.name} to canvas`}
    >
      <Icon className="text-muted-foreground h-4 w-4 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-foreground truncate text-xs font-medium">{component.name}</div>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground truncate text-[10px]">{category}</span>
          <CompatibilityBadge
            badge={component.compatibility_badge}
            className="!px-1 !py-0 !text-[8px]"
          />
        </div>
      </div>
    </div>
  );
}

export function ComponentPalette() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const { data, isLoading } = useComponents({
    pageSize: 100,
    category: activeCategory === "all" ? undefined : activeCategory,
    search: search || undefined,
  });

  const components = data?.items ?? [];

  return (
    <div className="flex h-full flex-col">
      {/* Search */}
      <div className="border-border border-b p-2">
        <div className="relative">
          <Search className="text-muted-foreground absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search components..."
            className="border-input bg-background text-foreground placeholder:text-muted-foreground focus:ring-ring w-full rounded border py-1.5 pl-7 pr-2 text-xs focus:outline-none focus:ring-1"
          />
        </div>
      </div>

      {/* Category pills */}
      <div className="border-border flex flex-wrap gap-1 border-b p-2">
        <button
          type="button"
          onClick={() => setActiveCategory("all")}
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
            activeCategory === "all"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:text-foreground"
          }`}
        >
          {"All"}
        </button>
        {SECTION_CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setActiveCategory(cat)}
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Component list */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="border-border bg-muted h-12 animate-pulse rounded border" />
            ))}
          </div>
        ) : components.length === 0 ? (
          <div className="text-muted-foreground py-8 text-center text-xs">
            {"No components found"}
          </div>
        ) : (
          <div className="space-y-1.5">
            {components.map((comp) => (
              <PaletteCard key={comp.id} component={comp} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
