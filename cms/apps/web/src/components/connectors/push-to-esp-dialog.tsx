"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";
import { useESPConnections, usePushToESP } from "@/hooks/use-esp-sync";
import { ESP_LABELS } from "@/types/esp-sync";

interface PushToESPDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templateId: number;
  templateName: string;
  projectId: number;
}

export function PushToESPDialog({
  open,
  onOpenChange,
  templateId,
  templateName,
  projectId,
}: PushToESPDialogProps) {
  const { data: connections } = useESPConnections();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Reset selection when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setSelectedId(null);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const projectConnections = useMemo(
    () => (connections ?? []).filter((c) => c.project_id === projectId && c.status === "connected"),
    [connections, projectId],
  );

  const selectedConnection = projectConnections.find((c) => c.id === selectedId) ?? null;
  const { trigger, isMutating } = usePushToESP(selectedId);

  const handlePush = async () => {
    if (!selectedId || !selectedConnection) return;
    try {
      await trigger({ template_id: templateId });
      const espLabel = ESP_LABELS[selectedConnection.esp_type]?.label ?? selectedConnection.esp_type;
      toast.success(`Template pushed to \${espLabel}`);
      onOpenChange(false);
    } catch {
      toast.error("Failed to push template");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle>{"Push to ESP"}</DialogTitle>
          <DialogDescription>
            {"Push this template to a connected ESP"} &mdash; {templateName}
          </DialogDescription>
        </DialogHeader>

        {projectConnections.length === 0 ? (
          <p className="py-4 text-center text-sm text-foreground-muted">
            {"No ESP connections for this project"}
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">{"Select connection"}</p>
            {projectConnections.map((conn) => {
              const espInfo = ESP_LABELS[conn.esp_type] ?? {
                label: conn.esp_type,
                color: "bg-surface-muted text-foreground-muted",
              };
              return (
                <button
                  key={conn.id}
                  type="button"
                  onClick={() => setSelectedId(conn.id)}
                  className={`flex w-full items-center gap-3 rounded-md border-2 p-3 text-left transition-colors ${
                    selectedId === conn.id
                      ? "border-interactive ring-1 ring-interactive"
                      : "border-card-border hover:bg-surface-hover"
                  }`}
                >
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${espInfo.color}`}>
                    {espInfo.label}
                  </span>
                  <span className="text-sm font-medium text-foreground">{conn.name}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handlePush}
            disabled={!selectedId || isMutating}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Pushing…"}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Upload className="h-4 w-4" />
                {"Push Template"}
              </span>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
