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
import { useCreateComponent } from "@/hooks/use-components";

const CATEGORIES = [
  { value: "structure", label: "Structure" },
  { value: "content", label: "Content" },
  { value: "navigation", label: "Navigation" },
  { value: "social", label: "Social" },
  { value: "footer", label: "Footer" },
  { value: "utility", label: "Utility" },
] as const;

interface CreateComponentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateComponentDialog({
  open,
  onOpenChange,
}: CreateComponentDialogProps) {
  const { trigger, isMutating } = useCreateComponent();
  const { mutate } = useSWRConfig();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("structure");
  const [htmlSource, setHtmlSource] = useState("");
  const [cssSource, setCssSource] = useState("");

  // React 19 reset pattern
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setName("");
    setSlug("");
    setDescription("");
    setCategory("structure");
    setHtmlSource("");
    setCssSource("");
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const autoSlug = (value: string) => {
    setName(value);
    setSlug(
      value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
    );
  };

  const isValid = name.trim().length >= 1 && slug.trim().length >= 1 && htmlSource.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await trigger({
        name: name.trim(),
        slug: slug.trim(),
        description: description.trim() || undefined,
        category,
        html_source: htmlSource,
        css_source: cssSource.trim() || undefined,
      });
      await mutate(
        (key: unknown) =>
          typeof key === "string" && key.startsWith("/api/v1/components"),
        undefined,
        { revalidate: true }
      );
      toast.success("Component created successfully");
      onOpenChange(false);
    } catch {
      toast.error("Failed to create component");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  const selectClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[32rem] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{"Create Component"}</DialogTitle>
          <DialogDescription>
            {"Add a new reusable email component to the library."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label
              htmlFor="comp-name"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"Name"}
            </label>
            <input
              id="comp-name"
              type="text"
              value={name}
              onChange={(e) => autoSlug(e.target.value)}
              placeholder="e.g., Hero Banner"
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Slug */}
          <div>
            <label
              htmlFor="comp-slug"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"Slug"}
            </label>
            <input
              id="comp-slug"
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="hero-banner"
              maxLength={200}
              disabled={isMutating}
              className={inputClass}
            />
          </div>

          {/* Description + Category */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="comp-desc"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {"Description"}
              </label>
              <input
                id="comp-desc"
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
                disabled={isMutating}
                className={inputClass}
              />
            </div>
            <div>
              <label
                htmlFor="comp-cat"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {"Category"}
              </label>
              <select
                id="comp-cat"
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

          {/* HTML Source */}
          <div>
            <label
              htmlFor="comp-html"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"HTML Source"}
            </label>
            <textarea
              id="comp-html"
              value={htmlSource}
              onChange={(e) => setHtmlSource(e.target.value)}
              placeholder="<table>...</table>"
              rows={6}
              disabled={isMutating}
              className={inputClass + " resize-none font-mono text-xs"}
            />
          </div>

          {/* CSS Source (optional) */}
          <div>
            <label
              htmlFor="comp-css"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"CSS Source"}
              <span className="ml-1 font-normal text-foreground-muted">
                {"(optional)"}
              </span>
            </label>
            <textarea
              id="comp-css"
              value={cssSource}
              onChange={(e) => setCssSource(e.target.value)}
              placeholder=".component { ... }"
              rows={3}
              disabled={isMutating}
              className={inputClass + " resize-none font-mono text-xs"}
            />
          </div>
        </div>

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
            onClick={handleSubmit}
            disabled={!isValid || isMutating}
            className="rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Creating..."}
              </span>
            ) : (
              "Create Component"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
