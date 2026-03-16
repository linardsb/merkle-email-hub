"use client";

import { useTranslations } from "next-intl";
import { Camera } from "lucide-react";
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
  const t = useTranslations("visualQa");

  if (screenshots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-foreground-muted">
        <Camera className="h-10 w-10" />
        <p className="text-sm">{t("noScreenshots")}</p>
        <p className="text-xs">{t("captureFirst")}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {screenshots.map((screenshot) => {
        const displayName =
          CLIENT_DISPLAY_NAMES[screenshot.client_name as ClientProfile] ??
          screenshot.client_name;
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
              <span className="text-sm font-medium text-foreground">
                {displayName}
              </span>
              <span className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted">
                {screenshot.viewport}
              </span>
            </div>

            {/* Screenshot image */}
            <div className="overflow-hidden rounded-md border border-border bg-surface-muted">
              <img
                src={`data:image/png;base64,${screenshot.image_base64}`}
                alt={t("clientScreenshotAlt", { client: displayName })}
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
