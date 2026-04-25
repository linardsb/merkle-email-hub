"use client";

import { Camera } from "../icons";
import type { ClientScreenshot, ClientProfile } from "@/types/rendering";
import { CLIENT_DISPLAY_NAMES } from "@/types/rendering";

interface ClientComparisonGridProps {
  screenshots: ClientScreenshot[];
  onSelectClient: (clientName: string) => void;
  selectedClient: string | null;
}

export function ClientComparisonGrid({
  screenshots,
  onSelectClient,
  selectedClient,
}: ClientComparisonGridProps) {
  if (screenshots.length === 0) {
    return (
      <div className="text-foreground-muted flex flex-col items-center justify-center gap-3 py-16">
        <Camera className="h-10 w-10" />
        <p className="text-sm">{"No screenshots captured yet"}</p>
        <p className="text-xs">{"Capture screenshots to begin visual QA review"}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {screenshots.map((screenshot) => {
        const displayName =
          CLIENT_DISPLAY_NAMES[screenshot.client_name as ClientProfile] ?? screenshot.client_name;
        const isSelected = selectedClient === screenshot.client_name;

        return (
          <button
            key={screenshot.client_name}
            type="button"
            onClick={() => onSelectClient(screenshot.client_name)}
            className={`rounded-lg border p-3 text-left transition-colors ${
              isSelected
                ? "border-interactive bg-interactive/5"
                : "border-card-border bg-card hover:border-interactive/50"
            }`}
          >
            {/* Header */}
            <div className="mb-2 flex items-center justify-between">
              <span className="text-foreground text-sm font-medium">{displayName}</span>
              <span className="bg-surface-muted text-foreground-muted rounded px-1.5 py-0.5 text-xs">
                {screenshot.viewport}
              </span>
            </div>

            {/* Screenshot image */}
            <div className="border-border bg-surface-muted overflow-hidden rounded-md border">
              <img
                src={`data:image/png;base64,${screenshot.image_base64}`}
                alt={`${displayName} screenshot`}
                className="h-auto max-h-96 w-full object-contain"
                loading="lazy"
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}
