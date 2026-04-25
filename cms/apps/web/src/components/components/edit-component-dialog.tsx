"use client";

import { useState } from "react";
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
import { useUpdateComponent } from "@/hooks/use-components";
import type { ComponentResponse } from "@email-hub/sdk";

const CATEGORIES = [
  { value: "structure", label: "Structure" },
  { value: "content", label: "Content" },
  { value: "navigation", label: "Navigation" },
  { value: "social", label: "Social" },
  { value: "footer", label: "Footer" },
  { value: "utility", label: "Utility" },
] as const;

interface EditComponentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  component: ComponentResponse;
}

export function EditComponentDialog({ open, onOpenChange, component }: EditComponentDialogProps) {
  const { trigger, isMutating } = useUpdateComponent(component.id);
  const { mutate } = useSWRConfig();

  const [name, setName] = useState(component.name);
  const [description, setDescription] = useState(component.description ?? "");
  const [category, setCategory] = useState(component.category ?? "structure");

  // React 19 reset pattern
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName(component.name);
    setDescription(component.description ?? "");
    setCategory(component.category ?? "structure");
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const isValid = name.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await trigger({
        name: name.trim(),
        description: description.trim() || undefined,
        category,
      });
      await mutate(
        (key: unknown) => typeof key === "string" && key.startsWith("/api/v1/components"),
        undefined,
        { revalidate: true },
      );
      toast.success("Component updated");
      onOpenChange(false);
    } catch {
      toast.error("Failed to update component");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle>{"Edit Component"}</DialogTitle>
          <DialogDescription>{"Update component metadata."}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="edit-comp-name"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Name"}
            </label>
            <input
              id="edit-comp-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          <div>
            <label
              htmlFor="edit-comp-desc"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Description"}
            </label>
            <textarea
              id="edit-comp-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              disabled={isMutating}
              className={inputClass + " resize-none"}
            />
          </div>

          <div>
            <label
              htmlFor="edit-comp-cat"
              className="text-foreground mb-1.5 block text-sm font-medium"
            >
              {"Category"}
            </label>
            <select
              id="edit-comp-cat"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isMutating}
              className={selectClass}
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="border-border text-foreground hover:bg-surface-hover rounded-md border px-3 py-1.5 text-sm transition-colors"
          >
            {"Cancel"}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || isMutating}
            className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Saving..."}
              </span>
            ) : (
              "Save Changes"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
