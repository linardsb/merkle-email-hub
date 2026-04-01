"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Calendar, Users, Paperclip, Tag, AlertCircle, Loader2, ExternalLink, ImageOff, Building2, Puzzle, Link as LinkIcon } from "../icons";
import { useBriefDetail } from "@/hooks/use-briefs";
import { BriefPlatformBadge } from "./brief-platform-badge";
import { BriefResourceLinks } from "./brief-resource-links";
import type { DesignConnection } from "@/types/design-sync";

interface BriefDetailDialogProps {
  itemId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  designConnection?: DesignConnection | null;
  onSyncDesign?: (connectionId: number) => void;
  onConnectDesign?: () => void;
}

export function BriefDetailDialog({ itemId, open, onOpenChange, designConnection, onSyncDesign, onConnectDesign }: BriefDetailDialogProps) {
  const { data: detail, isLoading } = useBriefDetail(open ? itemId : null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem]">
        <DialogHeader>
          <div className="flex items-center justify-between gap-2">
            <DialogTitle className="text-base">
              {detail?.external_id ? `${detail.external_id} — ` : ""}
              {detail?.title ?? "Brief Details"}
            </DialogTitle>
            {detail?.platform && (
              <BriefPlatformBadge platform={detail.platform} />
            )}
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
          </div>
        ) : detail ? (
          <div className="space-y-4">
            {/* Thumbnail */}
            {detail.thumbnail_url ? (
              <div className="overflow-hidden rounded-md">
                <img
                  src={detail.thumbnail_url}
                  alt={detail.title}
                  className="w-full object-cover"
                  style={{ maxHeight: "12rem" }}
                />
              </div>
            ) : null}

            {/* Client + Meta */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-foreground-muted">
              {detail.client_name && (
                <span className="flex items-center gap-1 rounded-full bg-interactive/15 px-2 py-0.5 font-semibold text-interactive">
                  <Building2 className="h-3 w-3" />
                  {detail.client_name}
                </span>
              )}
              {detail.priority && (
                <span className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  {`Priority: ${detail.priority}`}
                </span>
              )}
              {detail.assignees.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {detail.assignees.join(", ")}
                </span>
              )}
              {detail.due_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(detail.due_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
              )}
              {detail.connection_name && (
                <span className="flex items-center gap-1">
                  <ExternalLink className="h-3 w-3" />
                  {detail.connection_name}
                </span>
              )}
            </div>

            {/* Labels */}
            {detail.labels.length > 0 && (
              <div className="flex flex-wrap gap-1">
                <Tag className="mt-0.5 h-3 w-3 text-foreground-muted" />
                {detail.labels.map((label) => (
                  <span
                    key={label}
                    className="rounded bg-surface-muted px-1.5 py-0.5 text-xs text-foreground-muted"
                  >
                    {label}
                  </span>
                ))}
              </div>
            )}

            {/* Description */}
            <div className="prose-sm max-h-60 overflow-y-auto rounded border border-card-border bg-surface-muted p-3 text-sm text-foreground whitespace-pre-wrap">
              {detail.description || "No description available"}
            </div>

            {/* Design sync action */}
            {designConnection ? (
              <button
                type="button"
                onClick={() => onSyncDesign?.(designConnection.id)}
                className="flex items-center gap-2 rounded-md border border-interactive/20 bg-interactive/5 px-4 py-3 text-sm font-medium text-interactive transition-colors hover:bg-interactive/10"
              >
                <Puzzle className="h-4 w-4" />
                Sync & Extract Components
                <span className="ml-auto text-xs text-foreground-muted">
                  {designConnection.provider === "figma" ? "from Figma" :
                   designConnection.provider === "sketch" ? "from Sketch" :
                   `from ${designConnection.provider}`}
                </span>
              </button>
            ) : onConnectDesign ? (
              <button
                type="button"
                onClick={onConnectDesign}
                className="flex items-center gap-2 rounded-md border border-dashed border-foreground-muted/30 px-4 py-3 text-sm text-foreground-muted transition-colors hover:border-interactive/40 hover:text-interactive"
              >
                <LinkIcon className="h-4 w-4" />
                Connect Design File
              </button>
            ) : null}

            {/* Resources */}
            {detail.resources && detail.resources.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-medium text-foreground">{"Resources"}</p>
                <BriefResourceLinks resources={detail.resources} maxVisible={10} />
              </div>
            )}

            {/* Attachments */}
            {detail.attachments.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-medium text-foreground">{"Attachments"}</p>
                <div className="space-y-1">
                  {detail.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center gap-2 rounded border border-card-border px-2 py-1.5 text-xs text-foreground-muted"
                    >
                      <Paperclip className="h-3 w-3 shrink-0" />
                      <span className="truncate">{att.filename}</span>
                      <span className="ml-auto shrink-0">
                        {(att.size_bytes / 1024).toFixed(0)} KB
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-foreground-muted">{"Brief not found"}</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
