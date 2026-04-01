"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "../icons";
import { toast } from "sonner";
import { useSWRConfig } from "swr";
import { useDeleteComponent } from "@/hooks/use-components";

interface DeleteComponentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  componentId: number;
  componentName: string;
}

export function DeleteComponentDialog({
  open,
  onOpenChange,
  componentId,
  componentName,
}: DeleteComponentDialogProps) {
  const { trigger, isMutating } = useDeleteComponent(componentId);
  const { mutate } = useSWRConfig();

  const handleDelete = async () => {
    try {
      await trigger(undefined as never);
      await mutate(
        (key: unknown) =>
          typeof key === "string" && key.startsWith("/api/v1/components"),
        undefined,
        { revalidate: true }
      );
      toast.success("Component deleted");
      onOpenChange(false);
    } catch {
      toast.error("Failed to delete component");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[24rem]">
        <DialogHeader>
          <DialogTitle>{"Delete Component"}</DialogTitle>
          <DialogDescription>
            {`Are you sure you want to delete "${componentName}"? This action cannot be undone.`}
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={isMutating}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover disabled:opacity-50"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isMutating}
            className="rounded-md bg-status-danger px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-status-danger/90 disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Deleting..."}
              </span>
            ) : (
              "Delete"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
