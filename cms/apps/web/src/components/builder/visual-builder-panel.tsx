"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { authFetch } from "@/lib/auth-fetch";
import { useBuilderState, useBuilderPreview, createSectionDefaults } from "@/hooks/use-builder";
import { DragDropContext } from "./drag-drop-context";
import { ComponentPalette } from "./component-palette";
import { BuilderCanvas } from "./builder-canvas";
import { BuilderPreview } from "./builder-preview";
import { ZoomControls } from "./zoom-controls";
import { PropertyPanel } from "./panels";
import {
  DEFAULT_RESPONSIVE,
  DEFAULT_ADVANCED,
  type BuilderSection,
  type SectionNode,
  type SlotDefinition,
  type DefaultTokens,
} from "@/types/visual-builder";
import type { DesignSystemConfig } from "@/types/design-system-config";
import type {
  AppComponentsSchemasVersionResponse as VersionResponse,
  ComponentResponse,
} from "@email-hub/sdk";
import {
  BuilderToolbar,
  DEVICE_WIDTHS,
  type DevicePreview,
  type ClientPreview,
} from "@/components/workspace/builder-toolbar";
import { BuilderOnboarding } from "@/components/workspace/builder-onboarding";
import { ImportDialog } from "./import-dialog";

/**
 * Infer minimal SlotDefinition[] from data-slot-name elements in HTML.
 * Fallback when component metadata is unavailable (e.g. componentId=0).
 * @internal Exported for testing only.
 */
export function inferSlotDefinitions(htmlFragment: string): SlotDefinition[] {
  const temp = document.createElement("div");
  temp.innerHTML = htmlFragment;
  const slotEls = temp.querySelectorAll("[data-slot-name]");
  const seen = new Set<string>();
  const defs: SlotDefinition[] = [];
  for (const el of slotEls) {
    const slotId = el.getAttribute("data-slot-name");
    if (!slotId || seen.has(slotId)) continue;
    seen.add(slotId);
    // Determine slot type from element
    const tag = el.tagName.toLowerCase();
    let slotType: SlotDefinition["slot_type"] = "body";
    if (tag === "a") slotType = "cta";
    else if (tag === "img") slotType = "image";
    else if (tag === "h1" || tag === "h2" || tag === "h3") slotType = "headline";
    defs.push({
      slot_id: slotId,
      slot_type: slotType,
      selector: `[data-slot-name="${slotId}"]`,
      required: false,
      max_chars: null,
      placeholder: el.innerHTML,
      label: slotId.replace(/_/g, " "),
    });
  }
  return defs;
}

/**
 * Convert a parsed SectionNode to a BuilderSection with sensible defaults.
 * @internal Exported for testing only.
 */
export function sectionNodeToBuilderSection(
  node: SectionNode,
  versionCache?: Map<number, VersionResponse>,
): BuilderSection {
  // Try to resolve slot definitions from cached component metadata
  let slotDefinitions: SlotDefinition[] = [];
  let defaultTokens: DefaultTokens | null = null;

  if (node.componentId > 0 && versionCache?.has(node.componentId)) {
    const version = versionCache.get(node.componentId);
    const versionObj = version as Record<string, unknown> | undefined;
    if (versionObj && Array.isArray(versionObj["slot_definitions"])) {
      slotDefinitions = versionObj["slot_definitions"] as SlotDefinition[];
    }
    if (versionObj?.["default_tokens"] && typeof versionObj["default_tokens"] === "object") {
      defaultTokens = versionObj["default_tokens"] as DefaultTokens;
    }
  }

  // Fallback: infer slot definitions from data-slot-name attributes in HTML
  if (slotDefinitions.length === 0) {
    slotDefinitions = inferSlotDefinitions(node.htmlFragment);
  }

  return {
    id: node.id,
    componentId: node.componentId,
    componentName: node.componentName,
    componentSlug: "",
    category: "content",
    html: node.htmlFragment,
    css: null,
    slotFills: node.slotValues,
    tokenOverrides: node.styleOverrides,
    slotDefinitions,
    defaultTokens,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
  };
}

interface VisualBuilderPanelProps {
  code: string;
  onCodeChange: (code: string) => void;
  projectId?: number;
  /** Sections parsed from code editor (split mode sync) */
  syncedSections?: SectionNode[];
  /** Original template shell from ESP import / sync engine */
  templateShell?: string;
  /** Emit section nodes when builder sections change (for sync engine in split mode) */
  onSectionsChange?: (sections: SectionNode[]) => void;
  /** Builder toolbar callbacks */
  onRunQA?: () => void;
  isRunningQA?: boolean;
  onAISuggest?: () => void;
  onCopyHtml?: () => void;
  onDownloadHtml?: () => void;
  onPushToESP?: () => void;
  /** QA section highlighting */
  onHighlightSection?: (sectionId: string) => void;
}

export function VisualBuilderPanel({
  code,
  onCodeChange,
  projectId,
  syncedSections,
  templateShell,
  onSectionsChange,
  onRunQA,
  isRunningQA,
  onAISuggest,
  onCopyHtml,
  onDownloadHtml,
  onPushToESP,
}: VisualBuilderPanelProps) {
  const {
    sections,
    selectedSectionId,
    addSection,
    removeSection,
    duplicateSection,
    moveSection,
    updateSection,
    selectSection,
    setSections,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useBuilderState();

  const [zoom, setZoom] = useState(100);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [designSystem, setDesignSystem] = useState<DesignSystemConfig | null>(null);
  const [devicePreview, setDevicePreview] = useState<DevicePreview>("desktop");
  const [clientPreview, setClientPreview] = useState<ClientPreview>("none");
  // Map device preview to legacy previewMode for property panel
  const previewMode = devicePreview === "mobile" ? "mobile" : "desktop";
  const htmlCacheRef = useRef<Map<number, VersionResponse>>(new Map());
  const lastEmittedHtmlRef = useRef<string | null>(null);

  const assembledHtml = useBuilderPreview(sections, templateShell);

  // Fetch design system for the project
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await authFetch(`/api/v1/projects/${projectId}/design-system`);
        if (!res.ok || cancelled) return;
        const data: DesignSystemConfig = await res.json();
        if (!cancelled) setDesignSystem(data);
      } catch {
        // Design system is optional
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // Sync assembled HTML to code editor
  useEffect(() => {
    if (assembledHtml && assembledHtml !== lastEmittedHtmlRef.current) {
      lastEmittedHtmlRef.current = assembledHtml;
      onCodeChange(assembledHtml);
    }
  }, [assembledHtml, onCodeChange]);

  // Fetch component version HTML (used by both sync and palette drop)
  const fetchComponentHtml = useCallback(
    async (componentId: number): Promise<VersionResponse | null> => {
      const cached = htmlCacheRef.current.get(componentId);
      if (cached) return cached;

      try {
        const res = await authFetch(`/api/v1/components/${componentId}/versions`);
        if (!res.ok) return null;
        const versions: VersionResponse[] = await res.json();
        const latest = versions[0];
        if (!latest) return null;
        // Evict oldest entry if cache exceeds 50 components
        const cache = htmlCacheRef.current;
        if (cache.size >= 50) {
          const oldest = cache.keys().next().value;
          if (oldest !== undefined) cache.delete(oldest);
        }
        cache.set(componentId, latest);
        return latest;
      } catch {
        return null;
      }
    },
    [],
  );

  // Apply synced sections from code editor (split mode)
  // Guard: compare IDs to avoid feedback loops (builder -> code -> parse -> builder)
  const lastSyncedIdsRef = useRef<string>("");
  useEffect(() => {
    if (!syncedSections || syncedSections.length === 0) return;
    const incomingIds = syncedSections.map((s) => s.id).join(",");
    if (incomingIds === lastSyncedIdsRef.current) return;
    lastSyncedIdsRef.current = incomingIds;

    // Prefetch component metadata for known components, then convert
    let cancelled = false;
    (async () => {
      const unknownIds = syncedSections
        .filter((s) => s.componentId > 0 && !htmlCacheRef.current.has(s.componentId))
        .map((s) => s.componentId);
      // Deduplicate
      const uniqueIds = [...new Set(unknownIds)];
      await Promise.all(uniqueIds.map((id) => fetchComponentHtml(id)));
      if (cancelled) return;
      const builderSections = syncedSections.map((s) =>
        sectionNodeToBuilderSection(s, htmlCacheRef.current),
      );
      setSections(builderSections);
    })();
    return () => {
      cancelled = true;
    };
  }, [syncedSections, setSections, fetchComponentHtml]);

  // Emit SectionNode[] to parent when builder sections change (split mode sync)
  const lastEmittedSectionIdsRef = useRef<string>("");
  useEffect(() => {
    if (!onSectionsChange || sections.length === 0) return;
    // Guard against feedback loop: don't re-emit sections we just received
    const currentIds = sections.map((s) => s.id).join(",");
    if (currentIds === lastEmittedSectionIdsRef.current) return;
    if (currentIds === lastSyncedIdsRef.current) return;
    lastEmittedSectionIdsRef.current = currentIds;
    const nodes: SectionNode[] = sections.map((s) => ({
      id: s.id,
      componentId: s.componentId,
      componentName: s.componentName,
      slotValues: { ...s.slotFills },
      styleOverrides: {},
      htmlFragment: s.html,
    }));
    onSectionsChange(nodes);
  }, [sections, onSectionsChange]);

  // Handle palette drop
  const handleExternalDrop = useCallback(
    async (componentId: number, overId: string | null) => {
      const version = await fetchComponentHtml(componentId);
      if (!version) return;

      // Find the component data from the drag event data
      const component: Partial<ComponentResponse> = {
        id: componentId,
        name: `Component ${componentId}`,
      };

      // Extract slot definitions and default tokens from version response.
      // These fields exist on the API response but aren't in the SDK VersionResponse type.
      const versionObj = version as Record<string, unknown>;
      const slotDefinitions: SlotDefinition[] = Array.isArray(versionObj["slot_definitions"])
        ? (versionObj["slot_definitions"] as SlotDefinition[])
        : [];
      const defaultTokens: DefaultTokens | null =
        versionObj["default_tokens"] && typeof versionObj["default_tokens"] === "object"
          ? (versionObj["default_tokens"] as DefaultTokens)
          : null;

      const defaults = createSectionDefaults();

      const section: BuilderSection = {
        id: crypto.randomUUID(),
        componentId,
        componentName: component.name ?? `Component ${componentId}`,
        componentSlug: "",
        category: "content",
        html: version.html_source,
        css: version.css_source ?? null,
        slotFills: {},
        tokenOverrides: {},
        slotDefinitions,
        defaultTokens,
        responsive: defaults.responsive,
        advanced: defaults.advanced,
      };

      // Parse drop zone index from overId (format: "drop-zone-N")
      let atIndex: number | undefined;
      if (overId?.startsWith("drop-zone-")) {
        atIndex = parseInt(overId.replace("drop-zone-", ""), 10);
      }

      addSection(section, atIndex);
    },
    [fetchComponentHtml, addSection],
  );

  // Handle reorder
  const handleReorder = useCallback(
    (activeId: string, overId: string) => {
      const fromIndex = sections.findIndex((s) => s.id === activeId);
      const toIndex = sections.findIndex((s) => s.id === overId);
      if (fromIndex !== -1 && toIndex !== -1) {
        moveSection(fromIndex, toIndex);
      }
    },
    [sections, moveSection],
  );

  // Handle property panel updates
  const handlePropertyUpdate = useCallback(
    (updates: Partial<BuilderSection>) => {
      if (selectedSectionId) {
        updateSection(selectedSectionId, updates);
      }
    },
    [selectedSectionId, updateSection],
  );

  // Stable close callback for PropertyPanel (avoids Escape effect churn)
  const handlePanelClose = useCallback(() => selectSection(null), [selectSection]);

  // Import dialog: accept annotated HTML from import
  const handleImportAccept = useCallback(
    (annotatedHtml: string) => {
      onCodeChange(annotatedHtml);
    },
    [onCodeChange],
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrlOrMeta = e.ctrlKey || e.metaKey;

      if (isCtrlOrMeta && e.key === "z" && !e.shiftKey && canUndo) {
        e.preventDefault();
        undo();
      } else if (isCtrlOrMeta && e.key === "z" && e.shiftKey && canRedo) {
        e.preventDefault();
        redo();
      } else if (
        (e.key === "Delete" || e.key === "Backspace") &&
        selectedSectionId &&
        !isCtrlOrMeta
      ) {
        // Only if not in an input/textarea
        const target = e.target as HTMLElement;
        if (target.tagName !== "INPUT" && target.tagName !== "TEXTAREA") {
          e.preventDefault();
          removeSection(selectedSectionId);
        }
      } else if (isCtrlOrMeta && e.key === "d" && selectedSectionId) {
        e.preventDefault();
        duplicateSection(selectedSectionId);
      } else if (e.key === "ArrowUp" && selectedSectionId && isCtrlOrMeta) {
        e.preventDefault();
        const idx = sections.findIndex((s) => s.id === selectedSectionId);
        if (idx > 0) moveSection(idx, idx - 1);
      } else if (e.key === "ArrowDown" && selectedSectionId && isCtrlOrMeta) {
        e.preventDefault();
        const idx = sections.findIndex((s) => s.id === selectedSectionId);
        if (idx < sections.length - 1) moveSection(idx, idx + 1);
      } else if (e.key === "Escape") {
        selectSection(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    canUndo,
    canRedo,
    undo,
    redo,
    selectedSectionId,
    removeSection,
    duplicateSection,
    selectSection,
    sections,
    moveSection,
  ]);

  const selectedSection = selectedSectionId
    ? (sections.find((s) => s.id === selectedSectionId) ?? null)
    : null;

  // Preview width based on device mode
  const previewMaxWidth = DEVICE_WIDTHS[devicePreview];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <DragDropContext
        items={sections.map((s) => s.id)}
        onReorder={handleReorder}
        onExternalDrop={handleExternalDrop}
      >
        {/* Builder toolbar */}
        <div className="border-border flex items-center border-b">
          <button
            onClick={() => setImportDialogOpen(true)}
            className="border-input text-foreground hover:bg-accent ml-2 rounded-md border px-2 py-1 text-[10px] font-medium"
            title="Import HTML email"
          >
            Import HTML
          </button>
        </div>
        <BuilderToolbar
          devicePreview={devicePreview}
          onDevicePreviewChange={setDevicePreview}
          clientPreview={clientPreview}
          onClientPreviewChange={setClientPreview}
          onRunQA={onRunQA}
          isRunningQA={isRunningQA}
          onAISuggest={onAISuggest}
          onCopyHtml={onCopyHtml}
          onDownloadHtml={onDownloadHtml}
          onPushToESP={onPushToESP}
        />

        <div className="flex flex-1 overflow-hidden">
          {/* Palette sidebar */}
          <div
            className="border-border bg-card w-56 flex-shrink-0 overflow-hidden border-r"
            data-builder-palette
          >
            <ComponentPalette />
          </div>

          {/* Canvas + preview area */}
          <div className="bg-muted/30 flex flex-1 flex-col overflow-hidden">
            {sections.length > 0 ? (
              <>
                {/* Canvas */}
                <div className="flex-1 overflow-hidden" data-builder-canvas>
                  <BuilderCanvas
                    sections={sections}
                    selectedSectionId={selectedSectionId}
                    onSelect={selectSection}
                    onRemove={removeSection}
                    onDuplicate={duplicateSection}
                  />
                </div>

                {/* Preview + zoom */}
                <div className="border-border h-1/3 min-h-32 flex-shrink-0 border-t">
                  <div className="flex h-full flex-col">
                    <div className="border-border flex items-center justify-between border-b px-3 py-1">
                      <span className="text-muted-foreground text-[10px] font-medium">
                        {"Preview"}
                      </span>
                      <ZoomControls zoom={zoom} onZoomChange={setZoom} />
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <div
                        className="mx-auto h-full transition-all"
                        style={{ maxWidth: previewMaxWidth }}
                      >
                        <BuilderPreview assembledHtml={assembledHtml} zoom={zoom} />
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <BuilderCanvas
                sections={sections}
                selectedSectionId={selectedSectionId}
                onSelect={selectSection}
                onRemove={removeSection}
                onDuplicate={duplicateSection}
              />
            )}
          </div>

          {/* Property panel (right sidebar) */}
          {selectedSection && (
            <PropertyPanel
              section={selectedSection}
              onUpdate={handlePropertyUpdate}
              designSystem={designSystem}
              onClose={handlePanelClose}
              previewMode={previewMode}
              onPreviewModeChange={(mode) =>
                setDevicePreview(mode === "mobile" ? "mobile" : "desktop")
              }
            />
          )}
        </div>
      </DragDropContext>

      {/* Onboarding overlay */}
      <BuilderOnboarding />

      {/* Import dialog */}
      <ImportDialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        onAccept={handleImportAccept}
      />
    </div>
  );
}
