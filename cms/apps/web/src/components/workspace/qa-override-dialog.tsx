"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useQAOverride } from "@/hooks/use-qa";
import type { QACheckResult } from "@/types/qa";

const CHECK_LABELS: Record<string, string> = {
  html_validation: "HTML Validation",
  css_support: "CSS Support",
  file_size: "File Size",
  link_validation: "Link Validation",
  spam_score: "Spam Score",
  dark_mode: "Dark Mode",
  accessibility: "Accessibility",
  fallback: "Fallback Support",
  image_optimization: "Image Optimization",
  brand_compliance: "Brand Compliance",
};

interface QAOverrideDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  resultId: number;
  failedChecks: QACheckResult[];
  onSuccess: () => void;
}

export function QAOverrideDialog({
  open,
  onOpenChange,
  resultId,
  failedChecks,
  onSuccess,
}: QAOverrideDialogProps) {
  const { trigger: submitOverride, isMutating } = useQAOverride(resultId);

  const [justification, setJustification] = useState("");
  const [selectedChecks, setSelectedChecks] = useState<Set<string>>(new Set());

  // Reset state when dialog opens with (potentially) new checks
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setJustification("");
    setSelectedChecks(new Set(failedChecks.map((c) => c.check_name)));
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  const toggleCheck = (name: string) => {
    setSelectedChecks((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const isValid = justification.trim().length >= 10 && selectedChecks.size > 0;

  const handleSubmit = async () => {
    if (!isValid) return;
    try {
      await submitOverride({
        justification: justification.trim(),
        checks_overridden: Array.from(selectedChecks),
      });
      toast.success("QA checks overridden successfully");
      setJustification("");
      onSuccess();
    } catch {
      toast.error("Failed to override checks");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[28rem]">
        <DialogHeader>
          <DialogTitle>{"Override QA Checks"}</DialogTitle>
          <DialogDescription>{"Select which failing checks to override and provide justification. This action is audited."}</DialogDescription>
        </DialogHeader>

        {/* Check selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">
            {"Checks to override"}
          </label>
          <div className="space-y-1.5">
            {failedChecks.map((check) => (
              <label
                key={check.check_name}
                className="flex cursor-pointer items-center gap-2 rounded border border-border px-3 py-2 text-sm transition-colors hover:bg-surface-hover"
              >
                <input
                  type="checkbox"
                  checked={selectedChecks.has(check.check_name)}
                  onChange={() => toggleCheck(check.check_name)}
                  className="accent-interactive"
                />
                <span className="text-foreground">
                  {CHECK_LABELS[check.check_name] ?? check.check_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Justification */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">
            {"Justification"}
          </label>
          <textarea
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder={"Explain why these checks can be safely overridden..."}
            rows={3}
            className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
          />
          <p className="text-xs text-foreground-muted">
            {`Minimum \${10} characters required`}
          </p>
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
            className="rounded-md bg-status-warning px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:opacity-90 disabled:opacity-50"
          >
            {isMutating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                {"Submitting..."}
              </span>
            ) : (
              "Confirm Override"
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
