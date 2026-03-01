"use client";

import { useTranslations } from "next-intl";
import {
  Monitor,
  Tablet,
  Smartphone,
  Moon,
  Sun,
  ZoomIn,
  ZoomOut,
  RefreshCw,
} from "lucide-react";
import { PersonaSelector } from "./persona-selector";
import type { PersonaResponse } from "@merkle-email-hub/sdk";

export type Viewport = "desktop" | "tablet" | "mobile";

interface PreviewToolbarProps {
  viewport: Viewport;
  onViewportChange: (v: Viewport) => void;
  darkMode: boolean;
  onDarkModeToggle: () => void;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  buildTimeMs: number | null;
  isCompiling: boolean;
  onCompile: () => void;
  hasContent: boolean;
  personas: PersonaResponse[];
  selectedPersonaId: number | null;
  onPersonaSelect: (persona: PersonaResponse | null) => void;
  isLoadingPersonas?: boolean;
}

const viewportButtons = [
  { value: "desktop" as const, icon: Monitor, labelKey: "previewDesktop" },
  { value: "tablet" as const, icon: Tablet, labelKey: "previewTablet" },
  { value: "mobile" as const, icon: Smartphone, labelKey: "previewMobile" },
];

export function PreviewToolbar({
  viewport,
  onViewportChange,
  darkMode,
  onDarkModeToggle,
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  buildTimeMs,
  isCompiling,
  onCompile,
  hasContent,
  personas,
  selectedPersonaId,
  onPersonaSelect,
  isLoadingPersonas,
}: PreviewToolbarProps) {
  const t = useTranslations("workspace");

  return (
    <div className="flex h-8 items-center justify-between border-b border-border bg-card px-3 text-xs text-muted-foreground">
      {/* Left: Viewport + Dark mode */}
      <div className="flex items-center gap-2">
        <div className="flex items-center rounded border border-border">
          {viewportButtons.map(({ value, icon: Icon, labelKey }) => (
            <button
              key={value}
              type="button"
              onClick={() => onViewportChange(value)}
              className={`rounded p-1 transition-colors hover:bg-accent ${viewport === value ? "bg-accent text-foreground" : ""}`}
              title={t(labelKey)}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onDarkModeToggle}
          className={`rounded p-1 transition-colors hover:bg-accent ${darkMode ? "text-foreground" : ""}`}
          title={t("previewDarkMode")}
        >
          {darkMode ? (
            <Sun className="h-3.5 w-3.5" />
          ) : (
            <Moon className="h-3.5 w-3.5" />
          )}
        </button>

        <div className="h-4 w-px bg-border" />

        <PersonaSelector
          personas={personas}
          selectedPersonaId={selectedPersonaId}
          onSelect={onPersonaSelect}
          isLoading={isLoadingPersonas}
        />
      </div>

      {/* Right: Build time, Zoom, Compile */}
      <div className="flex items-center gap-2">
        {buildTimeMs !== null && (
          <span className="text-muted-foreground">
            {t("previewBuildTime", { time: buildTimeMs })}
          </span>
        )}

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onZoomOut}
            className="rounded p-1 transition-colors hover:bg-accent"
            title={t("previewZoomOut")}
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={onZoomReset}
            className="min-w-[3rem] text-center transition-colors hover:text-foreground"
            title={t("previewZoomReset")}
          >
            {t("previewZoomLevel", { level: zoom })}
          </button>
          <button
            type="button"
            onClick={onZoomIn}
            className="rounded p-1 transition-colors hover:bg-accent"
            title={t("previewZoomIn")}
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
        </div>

        <button
          type="button"
          onClick={onCompile}
          disabled={!hasContent || isCompiling}
          className="flex items-center gap-1 rounded px-1.5 py-1 transition-colors hover:bg-accent disabled:opacity-50"
          title={isCompiling ? t("previewCompiling") : t("previewCompile")}
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isCompiling ? "animate-spin" : ""}`}
          />
          <span>{isCompiling ? t("previewCompiling") : t("previewCompile")}</span>
        </button>
      </div>
    </div>
  );
}
