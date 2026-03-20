"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ChevronRight,
  ChevronDown,
  FileText,
  Frame,
  Group,
  Component,
  Type,
  Square,
  Loader2,
} from "lucide-react";
import { useDesignFileStructure, useExportImages } from "@/hooks/use-design-sync";
import type { DesignNode } from "@/types/design-sync";

interface DesignFileBrowserProps {
  connectionId: number;
  selectedNodeIds: string[];
  onSelectionChange: (nodeIds: string[]) => void;
}

const SELECTABLE_TYPES = new Set(["FRAME", "GROUP", "COMPONENT", "COMPONENT_SET", "INSTANCE", "SECTION"]);

function getNodeIcon(type: string) {
  switch (type) {
    case "PAGE":
    case "CANVAS":
      return FileText;
    case "FRAME":
    case "SECTION":
      return Frame;
    case "GROUP":
      return Group;
    case "COMPONENT":
    case "COMPONENT_SET":
      return Component;
    case "TEXT":
      return Type;
    default:
      return Square;
  }
}

/** Collect all selectable descendant IDs from a node */
function collectSelectableIds(node: DesignNode): string[] {
  const ids: string[] = [];
  if (SELECTABLE_TYPES.has(node.type)) {
    ids.push(node.id);
  }
  for (const child of node.children) {
    ids.push(...collectSelectableIds(child));
  }
  return ids;
}

/** Collect all FRAME-type IDs for thumbnail export */
function collectFrameIds(nodes: DesignNode[]): string[] {
  const ids: string[] = [];
  function walk(node: DesignNode) {
    if (node.type === "FRAME" || node.type === "SECTION") {
      ids.push(node.id);
    }
    for (const child of node.children) {
      walk(child);
    }
  }
  for (const n of nodes) walk(n);
  return ids;
}

interface TreeNodeProps {
  node: DesignNode;
  depth: number;
  selectedIds: Set<string>;
  expandedIds: Set<string>;
  thumbnails: Map<string, string>;
  onToggleExpand: (id: string) => void;
  onToggleSelect: (node: DesignNode) => void;
}

function TreeNode({
  node,
  depth,
  selectedIds,
  expandedIds,
  thumbnails,
  onToggleExpand,
  onToggleSelect,
}: TreeNodeProps) {
  const Icon = getNodeIcon(node.type);
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const isSelectable = SELECTABLE_TYPES.has(node.type);
  const isSelected = selectedIds.has(node.id);
  const isPage = node.type === "PAGE" || node.type === "CANVAS";
  const thumbnail = thumbnails.get(node.id);

  // Check partial selection (some children selected, not all)
  const selectableChildren = collectSelectableIds(node);
  const selectedChildCount = selectableChildren.filter((id) => selectedIds.has(id)).length;
  const isIndeterminate = !isSelected && selectedChildCount > 0 && selectedChildCount < selectableChildren.length;

  return (
    <div>
      <div
        className="flex items-center gap-1.5 rounded-md px-1.5 py-1 hover:bg-surface-hover"
        style={{ paddingLeft: `${depth * 1.25 + 0.375}rem` }}
      >
        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <button
            type="button"
            onClick={() => onToggleExpand(node.id)}
            className="flex h-5 w-5 shrink-0 items-center justify-center text-foreground-muted"
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}

        {/* Checkbox (only for selectable types) */}
        {isSelectable ? (
          <input
            type="checkbox"
            checked={isSelected}
            ref={(el) => {
              if (el) el.indeterminate = isIndeterminate;
            }}
            onChange={() => onToggleSelect(node)}
            className="h-3.5 w-3.5 shrink-0 rounded border-input-border accent-interactive"
          />
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        {/* Thumbnail or icon */}
        {thumbnail ? (
          <img
            src={thumbnail}
            alt={`Thumbnail for ${node.name}`}
            className="h-8 w-8 shrink-0 rounded border border-card-border object-cover"
          />
        ) : (
          <Icon className={`h-4 w-4 shrink-0 ${isPage ? "text-foreground" : "text-foreground-muted"}`} />
        )}

        {/* Node name */}
        <span className={`truncate text-sm ${isPage ? "font-medium text-foreground" : "text-foreground"}`}>
          {node.name}
        </span>

        {/* Dimensions */}
        {node.width !== null && node.height !== null && !isPage && (
          <span className="shrink-0 text-xs text-foreground-muted">
            {Math.round(node.width)}&times;{Math.round(node.height)}
          </span>
        )}
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedIds={selectedIds}
              expandedIds={expandedIds}
              thumbnails={thumbnails}
              onToggleExpand={onToggleExpand}
              onToggleSelect={onToggleSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function DesignFileBrowser({
  connectionId,
  selectedNodeIds,
  onSelectionChange,
}: DesignFileBrowserProps) {
  const { data: structure, isLoading, error } = useDesignFileStructure(connectionId);
  const { trigger: exportImages } = useExportImages();

  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [thumbnails, setThumbnails] = useState<Map<string, string>>(new Map());
  const [thumbnailsLoaded, setThumbnailsLoaded] = useState(false);

  const selectedSet = new Set(selectedNodeIds);

  // Stable ref for use in callbacks (avoids recreating callback on every selection change)
  const selectedNodeIdsRef = useRef(selectedNodeIds);
  selectedNodeIdsRef.current = selectedNodeIds;

  // Auto-expand pages on load
  useEffect(() => {
    if (structure?.pages) {
      setExpandedIds(new Set(structure.pages.map((p) => p.id)));
    }
  }, [structure]);

  // Fetch thumbnails for frame nodes
  useEffect(() => {
    if (!structure?.pages || thumbnailsLoaded) return;

    const frameIds = collectFrameIds(structure.pages);
    if (frameIds.length === 0) {
      setThumbnailsLoaded(true);
      return;
    }

    exportImages({
      connection_id: connectionId,
      node_ids: frameIds.slice(0, 50), // Limit batch size
      format: "png",
      scale: 0.5, // Small thumbnails
    })
      .then((result) => {
        const map = new Map<string, string>();
        for (const img of result.images) {
          map.set(img.node_id, img.url);
        }
        setThumbnails(map);
      })
      .catch(() => {
        // Thumbnails are non-critical — fail silently
      })
      .finally(() => setThumbnailsLoaded(true));
  }, [structure, connectionId, exportImages, thumbnailsLoaded]);

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleToggleSelect = useCallback(
    (node: DesignNode) => {
      const currentIds = selectedNodeIdsRef.current;
      const currentSet = new Set(currentIds);
      const descendantIds = collectSelectableIds(node);
      const allSelected = descendantIds.every((id) => currentSet.has(id));

      const next = new Set(currentIds);
      if (allSelected) {
        for (const id of descendantIds) next.delete(id);
      } else {
        for (const id of descendantIds) next.add(id);
      }
      onSelectionChange(Array.from(next));
    },
    [onSelectionChange, selectedNodeIdsRef],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
        <span className="ml-2 text-sm text-foreground-muted">{"Loading file structure…"}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg px-4 py-8 text-center">
        <p className="text-sm text-foreground-muted">{"Failed to load file structure"}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-2 text-sm font-medium text-interactive hover:underline"
        >
          {"Try again"}
        </button>
      </div>
    );
  }

  if (!structure?.pages || structure.pages.length === 0) {
    return (
      <div className="rounded-lg border border-card-border bg-card-bg px-4 py-8 text-center">
        <p className="text-sm text-foreground-muted">{"No pages found in this design file"}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">{"File Structure"}</h3>
        {selectedNodeIds.length > 0 && (
          <span className="text-xs text-foreground-muted">
            {`${selectedNodeIds.length} frames selected`}
          </span>
        )}
      </div>
      <div className="max-h-[24rem] overflow-y-auto rounded-lg border border-card-border bg-card-bg py-1">
        {structure.pages.map((page) => (
          <TreeNode
            key={page.id}
            node={page}
            depth={0}
            selectedIds={selectedSet}
            expandedIds={expandedIds}
            thumbnails={thumbnails}
            onToggleExpand={handleToggleExpand}
            onToggleSelect={handleToggleSelect}
          />
        ))}
      </div>
    </div>
  );
}
