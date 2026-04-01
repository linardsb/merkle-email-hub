"use client";

import { Code, Layout, Columns } from "../icons";
import type { SyncStatus } from "@/types/visual-builder";

export type ViewMode = "code" | "builder" | "split";

interface ViewSwitcherProps {
  activeView: ViewMode;
  onViewChange: (view: ViewMode) => void;
  syncStatus?: SyncStatus;
}

const VIEWS: { value: ViewMode; icon: React.ComponentType<{ className?: string }>; label: string }[] = [
  { value: "code", icon: Code, label: "Code" },
  { value: "builder", icon: Layout, label: "Builder" },
  { value: "split", icon: Columns, label: "Split" },
];

const SYNC_STATUS_COLORS: Record<SyncStatus, string> = {
  synced: "bg-success",
  syncing: "bg-warning animate-pulse",
  parse_error: "bg-destructive",
  conflict: "bg-destructive",
};

export function ViewSwitcher({ activeView, onViewChange, syncStatus }: ViewSwitcherProps) {
  const activeIndex = VIEWS.findIndex((v) => v.value === activeView);

  return (
    <div className="flex items-center gap-2 px-2 py-1.5">
      <div className="relative flex items-center rounded-md border border-border bg-muted/50 p-0.5">
        {/* Sliding background indicator */}
        <div
          className="absolute top-0.5 bottom-0.5 rounded-sm bg-background shadow-sm transition-transform duration-200 ease-out"
          style={{
            width: `calc(${100 / VIEWS.length}% - 2px)`,
            transform: `translateX(calc(${activeIndex} * 100% + ${activeIndex * 2}px))`,
            left: "1px",
          }}
        />

        {VIEWS.map(({ value, icon: Icon, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => onViewChange(value)}
            className={`relative z-10 flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-xs font-medium transition-colors ${
              activeView === value
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title={label}
          >
            <Icon className="h-3.5 w-3.5" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Sync status dot (split mode) */}
      {activeView === "split" && syncStatus && (
        <div className="flex items-center gap-1.5">
          <div className={`h-1.5 w-1.5 rounded-full ${SYNC_STATUS_COLORS[syncStatus]}`} />
          {syncStatus === "parse_error" && (
            <span className="text-[10px] text-destructive">{"Parse error"}</span>
          )}
        </div>
      )}
    </div>
  );
}
