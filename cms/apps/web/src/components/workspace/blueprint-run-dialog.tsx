"use client";

import { useCallback, useMemo, useState } from "react";
import {
  CheckCircle2,
  Zap,
  Search,
  FileText,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@email-hub/ui/components/ui/dialog";
import { Button } from "@email-hub/ui/components/ui/button";
import { Badge } from "@email-hub/ui/components/ui/badge";
import { Label } from "@email-hub/ui/components/ui/label";
import { Input } from "@email-hub/ui/components/ui/input";
import { useBlueprintRun } from "@/hooks/use-blueprint-run";
import { useAllBriefItems } from "@/hooks/use-briefs";
import { useBriefDetail } from "@/hooks/use-briefs";
import {
  PipelineTimeline,
  StatusBanner,
  CollapsibleHandoffs,
  formatNodeName,
} from "./blueprint/shared";
import type { BriefItem } from "@/types/briefs";

interface BlueprintRunDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  currentHtml: string;
  onApplyResult: (html: string) => void;
}

function BriefCard({
  brief,
  selected,
  onSelect,
}: {
  brief: BriefItem;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group relative flex gap-3 rounded-lg border p-2.5 text-left transition-colors ${
        selected
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : "border-border bg-card hover:border-muted-foreground/40"
      }`}
    >
      {/* Thumbnail */}
      <div className="h-20 w-28 shrink-0 overflow-hidden rounded-md bg-muted">
        {brief.thumbnail_url ? (
          <img
            src={brief.thumbnail_url}
            alt={brief.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <FileText className="h-8 w-8 text-muted-foreground/40" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {brief.title}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {brief.client_name && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              {brief.client_name}
            </Badge>
          )}
          {brief.platform && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              {brief.platform}
            </Badge>
          )}
        </div>
        {brief.labels.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {brief.labels.slice(0, 3).map((label) => (
              <span
                key={label}
                className="text-[10px] text-muted-foreground"
              >
                #{label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Selected indicator */}
      {selected && (
        <div className="absolute right-2 top-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
        </div>
      )}
    </button>
  );
}

export function BlueprintRunDialog({
  open,
  onOpenChange,
  projectId,
  currentHtml,
  onApplyResult,
}: BlueprintRunDialogProps) {
  const { run, isRunning, result, error, reset } = useBlueprintRun({ projectId });
  const { data: briefItems } = useAllBriefItems();

  const [selectedBriefId, setSelectedBriefId] = useState<number | null>(null);
  const [briefSearch, setBriefSearch] = useState("");
  const [includeHtml, setIncludeHtml] = useState(false);

  const { data: briefDetail } = useBriefDetail(selectedBriefId);

  const filteredBriefs = useMemo(() => {
    if (!briefItems) return [];
    if (!briefSearch.trim()) return briefItems;
    const q = briefSearch.toLowerCase();
    return briefItems.filter(
      (b) =>
        b.title.toLowerCase().includes(q) ||
        b.client_name?.toLowerCase().includes(q) ||
        b.labels.some((l) => l.toLowerCase().includes(q)),
    );
  }, [briefItems, briefSearch]);

  const selectedBrief = useMemo(
    () => briefItems?.find((b) => b.id === selectedBriefId) ?? null,
    [briefItems, selectedBriefId],
  );

  const handleRun = useCallback(async () => {
    if (!selectedBrief) return;

    const briefText = briefDetail?.description
      ? `${selectedBrief.title}\n\n${briefDetail.description}`
      : selectedBrief.title;

    await run({
      blueprint_name: "campaign",
      brief: briefText,
      initial_html: includeHtml ? currentHtml : undefined,
    });
  }, [selectedBrief, briefDetail, includeHtml, currentHtml, run]);

  const handleApply = useCallback(() => {
    if (result?.html) {
      onApplyResult(result.html);
      onOpenChange(false);
    }
  }, [result, onApplyResult, onOpenChange]);

  const handleClose = useCallback(() => {
    reset();
    setSelectedBriefId(null);
    setBriefSearch("");
    setIncludeHtml(false);
    onOpenChange(false);
  }, [reset, onOpenChange]);

  const totalTokens = result?.model_usage?.total_tokens ?? 0;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[52rem] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            {"Generate with Blueprint"}
          </DialogTitle>
          <DialogDescription>{"Run a multi-agent pipeline to generate, validate, and optimise your email template."}</DialogDescription>
        </DialogHeader>

        {!result && !isRunning && (
          <div className="space-y-4 py-2">
            {/* Blueprint selector */}
            <div>
              <Label className="text-sm font-medium">{"Pipeline"}</Label>
              <div className="mt-1.5 rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-sm font-medium text-foreground">
                  {"Full Campaign"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {"Generate a complete email from brief — scaffold, QA, fix, build, export"}
                </p>
              </div>
            </div>

            {/* Brief selector */}
            <div>
              <Label className="text-sm font-medium">{"Select a Brief"}</Label>
              <div className="relative mt-1.5">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={briefSearch}
                  onChange={(e) => setBriefSearch(e.target.value)}
                  placeholder={"Search briefs..."}
                  className="pl-9"
                />
              </div>
              <div className="mt-2 max-h-[20rem] overflow-y-auto rounded-lg border border-border">
                {!briefItems || briefItems.length === 0 ? (
                  <p className="p-4 text-center text-sm text-muted-foreground">
                    {"No briefs found. Connect a project management tool in the Briefs page."}
                  </p>
                ) : filteredBriefs.length === 0 ? (
                  <p className="p-4 text-center text-sm text-muted-foreground">
                    {"No briefs match your search."}
                  </p>
                ) : (
                  <div className="grid grid-cols-2 gap-2 p-2">
                    {filteredBriefs.map((brief) => (
                      <BriefCard
                        key={brief.id}
                        brief={brief}
                        selected={selectedBriefId === brief.id}
                        onSelect={() => setSelectedBriefId(brief.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Include HTML checkbox */}
            <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
              <input
                type="checkbox"
                checked={includeHtml}
                onChange={(e) => setIncludeHtml(e.target.checked)}
                className="h-4 w-4 rounded border-border"
              />
              {"Include current editor HTML as starting point"}
            </label>

            {error && (
              <p className="text-sm text-destructive">{"Blueprint run failed. Please try again."}</p>
            )}
          </div>
        )}

        {isRunning && (
          <div className="flex flex-col items-center justify-center gap-3 py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
            <p className="text-sm text-muted-foreground">{"Running..."}</p>
          </div>
        )}

        {result && (
          <div className="space-y-4 py-2">
            <StatusBanner status={result.status} qaPassed={result.qa_passed ?? false} />

            {/* Audience summary */}
            {result.audience_summary && (
              <div className="rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                  {"Audience Context"}
                </p>
                <p className="mt-1 text-xs text-foreground">{result.audience_summary}</p>
              </div>
            )}

            <PipelineTimeline progress={result.progress} />

            {/* Skipped nodes */}
            {(result.skipped_nodes ?? []).length > 0 && (
              <div className="rounded-lg border border-border bg-muted/50 p-3">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                  {"Skipped by routing"}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {(result.skipped_nodes ?? []).map((node) => (
                    <Badge key={node} variant="outline" className="text-xs">
                      {formatNodeName(node)}
                    </Badge>
                  ))}
                </div>
                {(result.routing_decisions ?? []).length > 0 && (
                  <div className="mt-2 space-y-1">
                    {(result.routing_decisions ?? [])
                      .filter((rd) => rd.action === "skip")
                      .map((rd, i) => (
                        <p key={i} className="text-xs text-muted-foreground">
                          <span className="font-medium">{formatNodeName(rd.node_name)}</span>
                          {" — "}
                          {rd.reason}
                        </p>
                      ))}
                  </div>
                )}
              </div>
            )}

            <CollapsibleHandoffs handoffs={result.handoff_history ?? []} />

            {/* Token usage */}
            {totalTokens > 0 && (
              <p className="text-xs text-muted-foreground">
                {`${totalTokens.toLocaleString()} tokens`}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          {!result && !isRunning && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {"Cancel"}
              </Button>
              <Button onClick={handleRun} disabled={!selectedBrief}>
                <Zap className="mr-1.5 h-3.5 w-3.5" />
                {"Run Pipeline"}
              </Button>
            </>
          )}
          {result && (
            <>
              <Button variant="outline" onClick={handleClose}>
                {"Close"}
              </Button>
              <Button onClick={handleApply}>
                {"Apply to Editor"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
