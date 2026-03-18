"use client";

import { useState } from "react";
import { X, Palette, ExternalLink } from "lucide-react";
import { ScrollArea } from "@email-hub/ui/components/ui/scroll-area";
import { Skeleton } from "@email-hub/ui/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@email-hub/ui/components/ui/select";
import {
  useDesignImportByTemplate,
  useDesignTokens,
  useDesignConnections,
} from "@/hooks/use-design-sync";
import { AssetViewer } from "./design-reference/asset-viewer";
import { TokenDisplay } from "./design-reference/token-display";
import type { EditorBridge } from "@/hooks/use-editor-bridge";

interface DesignReferencePanelProps {
  projectId: number;
  templateId: number | null;
  editor: EditorBridge;
  editorContent: string;
  hasEditorSelection: boolean;
  onClose: () => void;
}

export function DesignReferencePanel({
  projectId,
  templateId,
  editor,
  editorContent,
  hasEditorSelection,
  onClose,
}: DesignReferencePanelProps) {
  // Auto-detect: design import that produced this template
  const { data: autoImport, isLoading: autoLoading } =
    useDesignImportByTemplate(templateId, projectId);

  // Fallback: manual connection picker
  const [manualConnectionId, setManualConnectionId] = useState<number | null>(null);
  const { data: connections } = useDesignConnections();

  const activeConnectionId = autoImport?.connection_id ?? manualConnectionId;
  const hasAutoDetect = !!autoImport;
  const { data: tokens, isLoading: tokensLoading } = useDesignTokens(activeConnectionId);
  const activeConnection = connections?.find((c) => c.id === activeConnectionId);

  return (
    <div className="flex h-full w-80 flex-col border-l border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-foreground-muted" />
          <h3 className="text-sm font-semibold">{"Design Reference"}</h3>
        </div>
        <div className="flex items-center gap-1">
          {activeConnection?.file_url && (
            <a
              href={activeConnection.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 text-foreground-muted transition-colors hover:text-foreground"
              title={"Open in Figma"}
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-foreground-muted transition-colors hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 p-3">
          {/* Connection source */}
          {autoLoading ? (
            <Skeleton className="h-8 w-full" />
          ) : hasAutoDetect ? (
            <p className="text-xs text-foreground-muted">
              {`From design: \${activeConnection?.name ?? ""}`}
            </p>
          ) : (
            <div>
              <label className="mb-1 block text-xs text-foreground-muted">
                {"Design source"}
              </label>
              <Select
                value={manualConnectionId?.toString() ?? ""}
                onValueChange={(v) => setManualConnectionId(Number(v))}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder={"Select a connection…"} />
                </SelectTrigger>
                <SelectContent>
                  {connections
                    ?.filter((c) => c.project_id === projectId)
                    .map((c) => (
                      <SelectItem key={c.id} value={c.id.toString()}>
                        {c.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Design assets */}
          {autoImport?.assets && autoImport.assets.length > 0 && (
            <section>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground-muted">
                {"Design Assets"}
              </h4>
              <AssetViewer
                assets={autoImport.assets}
                connectionId={autoImport.connection_id}
              />
            </section>
          )}

          {/* Design tokens with all interactions */}
          {tokensLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-4 w-20" />
              <div className="grid grid-cols-4 gap-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-8" />
                ))}
              </div>
            </div>
          ) : tokens ? (
            <TokenDisplay
              tokens={tokens}
              editor={editor}
              editorContent={editorContent}
              hasSelection={hasEditorSelection}
            />
          ) : activeConnectionId ? (
            <p className="text-xs text-foreground-muted">{"No tokens extracted yet"}</p>
          ) : null}

          {/* Empty state */}
          {!autoLoading && !hasAutoDetect && !manualConnectionId && (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <Palette className="h-8 w-8 text-foreground-muted" />
              <p className="text-sm text-foreground-muted">{"No design linked"}</p>
              <p className="text-xs text-foreground-muted">{"This template wasn’t created from a Figma import. Select a design connection above to view tokens."}</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
