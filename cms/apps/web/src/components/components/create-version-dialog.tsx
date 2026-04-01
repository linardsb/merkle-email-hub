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
import { useCreateVersion } from "@/hooks/use-components";

interface CreateVersionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  componentId: number;
}

export function CreateVersionDialog({
  open,
  onOpenChange,
  componentId,
}: CreateVersionDialogProps) {
  const { trigger, isMutating } = useCreateVersion(componentId);
  const { mutate } = useSWRConfig();

  const [htmlSource, setHtmlSource] = useState("");
  const [cssSource, setCssSource] = useState("");
  const [changelog, setChangelog] = useState("");
  const [slotDefs, setSlotDefs] = useState("");
  const [defaultTokens, setDefaultTokens] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // React 19 reset pattern
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setHtmlSource("");
    setCssSource("");
    setChangelog("");
    setSlotDefs("");
    setDefaultTokens("");
    setShowAdvanced(false);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const isValid = htmlSource.trim().length >= 1;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      let parsedSlots: unknown[] | undefined;
      if (slotDefs.trim()) {
        try {
          const parsed: unknown = JSON.parse(slotDefs.trim());
          if (!Array.isArray(parsed)) {
            toast.error("Slot definitions must be a JSON array");
            return;
          }
          parsedSlots = parsed;
        } catch {
          toast.error("Slot definitions must be valid JSON");
          return;
        }
      }
      let parsedTokens: Record<string, unknown> | undefined;
      if (defaultTokens.trim()) {
        try {
          const parsed: unknown = JSON.parse(defaultTokens.trim());
          if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
            toast.error("Default tokens must be a JSON object");
            return;
          }
          parsedTokens = parsed as Record<string, unknown>;
        } catch {
          toast.error("Default tokens must be valid JSON");
          return;
        }
      }
      await trigger({
        html_source: htmlSource,
        css_source: cssSource.trim() || undefined,
        changelog: changelog.trim() || undefined,
        slot_definitions: parsedSlots,
        default_tokens: parsedTokens,
      });
      await mutate(
        (key: unknown) =>
          typeof key === "string" && key.startsWith("/api/v1/components"),
        undefined,
        { revalidate: true }
      );
      toast.success("Version created");
      onOpenChange(false);
    } catch {
      toast.error("Failed to create version");
    }
  };

  const inputClass =
    "w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus disabled:opacity-50";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[36rem] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{"Create New Version"}</DialogTitle>
          <DialogDescription>
            {"Upload updated HTML/CSS for this component."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* HTML Source */}
          <div>
            <label
              htmlFor="ver-html"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"HTML Source"}
            </label>
            <textarea
              id="ver-html"
              value={htmlSource}
              onChange={(e) => setHtmlSource(e.target.value)}
              placeholder="<table>...</table>"
              rows={8}
              disabled={isMutating}
              className={inputClass + " resize-none font-mono text-xs"}
            />
          </div>

          {/* CSS Source */}
          <div>
            <label
              htmlFor="ver-css"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"CSS Source"}
              <span className="ml-1 font-normal text-foreground-muted">
                {"(optional)"}
              </span>
            </label>
            <textarea
              id="ver-css"
              value={cssSource}
              onChange={(e) => setCssSource(e.target.value)}
              placeholder=".component { ... }"
              rows={4}
              disabled={isMutating}
              className={inputClass + " resize-none font-mono text-xs"}
            />
          </div>

          {/* Changelog */}
          <div>
            <label
              htmlFor="ver-changelog"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              {"Changelog"}
              <span className="ml-1 font-normal text-foreground-muted">
                {"(optional)"}
              </span>
            </label>
            <textarea
              id="ver-changelog"
              value={changelog}
              onChange={(e) => setChangelog(e.target.value)}
              placeholder="Describe what changed..."
              rows={2}
              disabled={isMutating}
              className={inputClass + " resize-none"}
            />
          </div>
        </div>

        {/* Advanced: Slot Definitions & Default Tokens */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs font-medium text-interactive hover:underline"
          >
            {showAdvanced ? "Hide advanced fields" : "Show advanced fields (slots, tokens)"}
          </button>
          {showAdvanced && (
            <div className="mt-3 space-y-4">
              <div>
                <label
                  htmlFor="ver-slots"
                  className="mb-1.5 block text-sm font-medium text-foreground"
                >
                  {"Slot Definitions"}
                  <span className="ml-1 font-normal text-foreground-muted">
                    {"(JSON, optional)"}
                  </span>
                </label>
                <textarea
                  id="ver-slots"
                  value={slotDefs}
                  onChange={(e) => setSlotDefs(e.target.value)}
                  placeholder={'[{"slot_id": "headline", "label": "Headline", "type": "text"}]'}
                  rows={3}
                  disabled={isMutating}
                  className={inputClass + " resize-none font-mono text-xs"}
                />
              </div>
              <div>
                <label
                  htmlFor="ver-tokens"
                  className="mb-1.5 block text-sm font-medium text-foreground"
                >
                  {"Default Tokens"}
                  <span className="ml-1 font-normal text-foreground-muted">
                    {"(JSON, optional)"}
                  </span>
                </label>
                <textarea
                  id="ver-tokens"
                  value={defaultTokens}
                  onChange={(e) => setDefaultTokens(e.target.value)}
                  placeholder={'{"bg_color": "#ffffff", "font_family": "Arial"}'}
                  rows={3}
                  disabled={isMutating}
                  className={inputClass + " resize-none font-mono text-xs"}
                />
              </div>
            </div>
          )}
        </div>

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
              "Create Version"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
