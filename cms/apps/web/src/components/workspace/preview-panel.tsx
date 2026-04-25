"use client";

import { useCallback, useState } from "react";
import { PreviewToolbar, type Viewport } from "./preview-toolbar";
import { PreviewIframe } from "./preview-iframe";
import type { PersonaResponse } from "@email-hub/sdk";

const ZOOM_STEPS = [50, 75, 100, 125, 150, 200] as const;

function mapWidthToViewport(width: number): Viewport {
  if (width <= 400) return "mobile";
  if (width <= 768) return "tablet";
  return "desktop";
}

interface PreviewPanelProps {
  compiledHtml: string | null;
  isCompiling: boolean;
  buildTimeMs: number | null;
  onCompile: () => void;
  hasContent: boolean;
  personas: PersonaResponse[];
  selectedPersonaId: number | null;
  onPersonaSelect: (persona: PersonaResponse | null) => void;
  isLoadingPersonas?: boolean;
}

export function PreviewPanel({
  compiledHtml,
  isCompiling,
  buildTimeMs,
  onCompile,
  hasContent,
  personas,
  selectedPersonaId,
  onPersonaSelect,
  isLoadingPersonas,
}: PreviewPanelProps) {
  const [viewport, setViewport] = useState<Viewport>("desktop");
  const [darkMode, setDarkMode] = useState(false);
  const [zoom, setZoom] = useState(100);

  const selectedPersona = personas.find((p) => p.id === selectedPersonaId);

  const handlePersonaSelect = useCallback(
    (persona: PersonaResponse | null) => {
      onPersonaSelect(persona);
      if (persona) {
        setViewport(mapWidthToViewport(persona.viewport_width ?? 600));
        setDarkMode(persona.dark_mode ?? false);
      }
    },
    [onPersonaSelect],
  );

  const handleViewportChange = useCallback(
    (v: Viewport) => {
      setViewport(v);
      onPersonaSelect(null);
    },
    [onPersonaSelect],
  );

  const handleDarkModeToggle = useCallback(() => {
    setDarkMode((d) => !d);
    onPersonaSelect(null);
  }, [onPersonaSelect]);

  const handleZoomIn = useCallback(() => {
    setZoom((current) => {
      const next = ZOOM_STEPS.find((s) => s > current);
      return next ?? current;
    });
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((current) => {
      const prev = [...ZOOM_STEPS].reverse().find((s) => s < current);
      return prev ?? current;
    });
  }, []);

  const handleZoomReset = useCallback(() => setZoom(100), []);

  return (
    <div className="bg-background flex h-full flex-col overflow-hidden">
      <PreviewToolbar
        viewport={viewport}
        onViewportChange={handleViewportChange}
        darkMode={darkMode}
        onDarkModeToggle={handleDarkModeToggle}
        zoom={zoom}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onZoomReset={handleZoomReset}
        buildTimeMs={buildTimeMs}
        isCompiling={isCompiling}
        onCompile={onCompile}
        hasContent={hasContent}
        personas={personas}
        selectedPersonaId={selectedPersonaId}
        onPersonaSelect={handlePersonaSelect}
        isLoadingPersonas={isLoadingPersonas}
      />
      <div className="flex-1 overflow-hidden">
        <PreviewIframe
          compiledHtml={compiledHtml}
          viewport={viewport}
          darkMode={darkMode}
          zoom={zoom}
          isCompiling={isCompiling}
          viewportWidthOverride={selectedPersona?.viewport_width ?? null}
        />
      </div>
    </div>
  );
}
