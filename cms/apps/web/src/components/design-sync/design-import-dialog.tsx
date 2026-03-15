"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";
import {
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Puzzle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { DesignFileBrowser } from "./design-file-browser";
import {
  useGenerateBrief,
  useCreateDesignImport,
  useConvertImport,
  useDesignImport,
  useDesignComponents,
  useExtractComponents,
} from "@/hooks/use-design-sync";
import type { GeneratedBrief, DesignImport } from "@/types/design-sync";

// ── Types ──

type ImportTab = "import" | "components";
type ImportStep = "select-frames" | "review-brief" | "converting" | "result";
type ExtractStep = "select-components" | "extracting" | "result";

interface DesignImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectionId: number;
  connectionName: string;
  initialNodeIds?: string[];
  initialTab?: ImportTab;
}

// ── Status badge ──

function StatusBadge({ status, t }: { status: string; t: ReturnType<typeof useTranslations> }) {
  const statusMap: Record<string, { className: string; key: string }> = {
    pending: { className: "bg-surface-hover text-foreground-muted", key: "statusPending" },
    extracting: { className: "bg-status-warning/10 text-status-warning", key: "statusExtracting" },
    converting: { className: "bg-interactive/10 text-interactive", key: "statusConverting" },
    completed: { className: "bg-status-success/10 text-status-success", key: "statusCompleted" },
    failed: { className: "bg-status-danger/10 text-status-danger", key: "statusFailed" },
    cancelled: { className: "bg-surface-hover text-foreground-muted", key: "statusCancelled" },
  };
  const fallback = { className: "bg-surface-hover text-foreground-muted", key: "statusPending" };
  const info = statusMap[status] ?? fallback;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${info.className}`}>
      {t(info.key)}
    </span>
  );
}

// ── Step indicator ──

function StepIndicator({ steps, currentIndex }: { steps: string[]; currentIndex: number }) {
  return (
    <div className="flex items-center gap-2">
      {steps.map((label, i) => (
        <div key={label} className="flex items-center gap-2">
          <div
            className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
              i < currentIndex
                ? "bg-status-success text-foreground-inverse"
                : i === currentIndex
                  ? "bg-interactive text-foreground-inverse"
                  : "bg-surface-hover text-foreground-muted"
            }`}
          >
            {i < currentIndex ? "\u2713" : i + 1}
          </div>
          <span
            className={`text-xs ${
              i === currentIndex ? "font-medium text-foreground" : "text-foreground-muted"
            }`}
          >
            {label}
          </span>
          {i < steps.length - 1 && (
            <div className="h-px w-6 bg-card-border" />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Import Design Tab ──

function ImportDesignWizard({
  connectionId,
  initialNodeIds,
  t,
}: {
  connectionId: number;
  initialNodeIds: string[];
  t: ReturnType<typeof useTranslations>;
}) {
  const router = useRouter();
  const [step, setStep] = useState<ImportStep>("select-frames");
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>(initialNodeIds);
  const [briefData, setBriefData] = useState<GeneratedBrief | null>(null);
  const [editedBrief, setEditedBrief] = useState("");
  const [importId, setImportId] = useState<number | null>(null);
  const [importResult, setImportResult] = useState<DesignImport | null>(null);

  const { trigger: generateBrief, isMutating: isGenerating } = useGenerateBrief();
  const { trigger: createImport, isMutating: isCreating } = useCreateDesignImport();
  const { trigger: triggerConvert } = useConvertImport(importId);
  const { data: polledImport } = useDesignImport(
    step === "converting" ? importId : null,
    true,
  );

  // Auto-advance when conversion completes
  useEffect(() => {
    if (!polledImport) return;
    if (polledImport.status === "completed" || polledImport.status === "failed") {
      setImportResult(polledImport);
      setStep("result");
    }
  }, [polledImport]);

  const steps = [
    t("stepSelectFrames"),
    t("stepReviewBrief"),
    t("stepConverting"),
    t("stepResult"),
  ];
  const stepIndex = ["select-frames", "review-brief", "converting", "result"].indexOf(step);

  const handleGenerateBrief = async () => {
    try {
      const result = await generateBrief({
        connection_id: connectionId,
        selected_node_ids: selectedNodeIds,
        include_tokens: true,
      });
      setBriefData(result);
      setEditedBrief(result.brief);
      setStep("review-brief");
    } catch {
      toast.error(t("fileBrowserError"));
    }
  };

  const handleStartConversion = async () => {
    try {
      const importResp = await createImport({
        connection_id: connectionId,
        brief: editedBrief,
        selected_node_ids: selectedNodeIds,
      });
      setImportId(importResp.id);
      await triggerConvert({ run_qa: true, output_mode: "structured" });
      setStep("converting");
    } catch {
      toast.error(t("statusFailed"));
    }
  };

  return (
    <div className="space-y-4">
      <StepIndicator steps={steps} currentIndex={stepIndex} />

      {/* Step 1: Select Frames */}
      {step === "select-frames" && (
        <div className="space-y-4">
          <p className="text-sm text-foreground-muted">{t("selectFrames")}</p>
          <DesignFileBrowser
            connectionId={connectionId}
            selectedNodeIds={selectedNodeIds}
            onSelectionChange={setSelectedNodeIds}
          />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleGenerateBrief}
              disabled={selectedNodeIds.length === 0 || isGenerating}
              className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("generatingBrief")}
                </>
              ) : (
                <>
                  {t("nextStep")}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Review Brief */}
      {step === "review-brief" && briefData && (
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-sm text-foreground-muted">
            <span>{t("layoutSummary", { summary: briefData.layout_summary })}</span>
            <span>{t("sectionsDetected", { count: briefData.sections_detected })}</span>
          </div>
          <div>
            <label htmlFor="import-brief" className="mb-1.5 block text-sm font-medium text-foreground">
              {t("briefLabel")}
            </label>
            <textarea
              id="import-brief"
              value={editedBrief}
              onChange={(e) => setEditedBrief(e.target.value)}
              rows={12}
              className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 font-mono text-sm text-foreground placeholder:text-input-placeholder focus:border-input-focus focus:outline-none focus:ring-1 focus:ring-input-focus"
            />
            <p className="mt-1 text-xs text-foreground-muted">{t("briefHint")}</p>
          </div>
          <div className="flex justify-between">
            <button
              type="button"
              onClick={() => setStep("select-frames")}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
            >
              <ArrowLeft className="h-4 w-4" />
              {t("backStep")}
            </button>
            <button
              type="button"
              onClick={handleStartConversion}
              disabled={editedBrief.trim().length < 10 || isCreating}
              className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
            >
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("startConversion")}
                </>
              ) : (
                t("startConversion")
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Converting */}
      {step === "converting" && (
        <div className="flex flex-col items-center gap-4 py-8">
          <Loader2 className="h-8 w-8 animate-spin text-interactive" />
          <p className="text-sm font-medium text-foreground">{t("convertingMessage")}</p>
          {polledImport && (
            <StatusBadge status={polledImport.status} t={t} />
          )}
        </div>
      )}

      {/* Step 4: Result */}
      {step === "result" && importResult && (
        <div className="flex flex-col items-center gap-4 py-6">
          {importResult.status === "completed" ? (
            <>
              <CheckCircle2 className="h-10 w-10 text-status-success" />
              <p className="text-sm font-medium text-foreground">{t("templateCreated")}</p>

              {/* Imported assets */}
              {importResult.assets.length > 0 && (
                <div className="w-full">
                  <h4 className="mb-2 text-sm font-medium text-foreground">
                    {t("importedAssets")}
                  </h4>
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                    {importResult.assets.map((asset) => (
                      <div
                        key={asset.id}
                        className="flex flex-col items-center gap-1 rounded-md border border-card-border bg-card-bg p-2"
                      >
                        <div className="h-12 w-12 rounded bg-surface-hover" />
                        <span className="truncate text-xs text-foreground-muted">
                          {asset.node_name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                {importResult.result_template_id && (
                  <button
                    type="button"
                    onClick={() =>
                      router.push(
                        `/projects/${importResult.project_id}/workspace?template=${importResult.result_template_id}`,
                      )
                    }
                    className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
                  >
                    <ExternalLink className="h-4 w-4" />
                    {t("openInWorkspace")}
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              <AlertCircle className="h-10 w-10 text-status-danger" />
              <p className="text-sm font-medium text-foreground">
                {t("conversionFailed", { error: importResult.error_message ?? "Unknown error" })}
              </p>
              <button
                type="button"
                onClick={() => setStep("review-brief")}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
              >
                {t("tryAgain")}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Extract Components Tab ──

function ExtractComponentsWizard({
  connectionId,
  t,
}: {
  connectionId: number;
  t: ReturnType<typeof useTranslations>;
}) {
  const [step, setStep] = useState<ExtractStep>("select-components");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [extractImportId, setExtractImportId] = useState<number | null>(null);
  const [totalComponents, setTotalComponents] = useState(0);
  const router = useRouter();

  const { data: componentList, isLoading } = useDesignComponents(connectionId);
  const { trigger: extractComponents, isMutating: isExtracting } = useExtractComponents(connectionId);
  const { data: polledImport } = useDesignImport(
    step === "extracting" ? extractImportId : null,
    true,
  );

  const components = componentList?.components ?? [];

  // Auto-advance when extraction completes
  useEffect(() => {
    if (!polledImport) return;
    if (polledImport.status === "completed" || polledImport.status === "failed") {
      setStep("result");
    }
  }, [polledImport]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const toggleAll = () => {
    if (selectedIds.length === components.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(components.map((c) => c.component_id));
    }
  };

  const handleExtract = async () => {
    try {
      const result = await extractComponents({
        component_ids: selectedIds.length === components.length ? undefined : selectedIds,
        generate_html: true,
      });
      setExtractImportId(result.import_id);
      setTotalComponents(result.total_components);
      setStep("extracting");
    } catch {
      toast.error(t("statusFailed"));
    }
  };

  // Step 1: Select Components
  if (step === "select-components") {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-5 w-5 animate-spin text-foreground-muted" />
        </div>
      );
    }

    if (components.length === 0) {
      return (
        <div className="rounded-lg border border-card-border bg-card-bg px-4 py-8 text-center">
          <Puzzle className="mx-auto mb-2 h-8 w-8 text-foreground-muted" />
          <p className="text-sm text-foreground-muted">{t("fileBrowserEmpty")}</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-foreground-muted">{t("selectComponents")}</p>
          <button
            type="button"
            onClick={toggleAll}
            className="text-xs font-medium text-interactive hover:underline"
          >
            {selectedIds.length === components.length ? t("deselectAll") : t("selectAll")}
          </button>
        </div>

        <div className="grid max-h-[20rem] grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3">
          {components.map((comp) => {
            const isSelected = selectedIds.includes(comp.component_id);
            return (
              <button
                key={comp.component_id}
                type="button"
                onClick={() => toggleSelect(comp.component_id)}
                className={`flex flex-col items-center gap-2 rounded-lg border-2 p-3 text-left transition-colors ${
                  isSelected
                    ? "border-interactive bg-interactive/5"
                    : "border-card-border bg-card-bg hover:bg-surface-hover"
                }`}
              >
                {comp.thumbnail_url ? (
                  <img
                    src={comp.thumbnail_url}
                    alt={t("thumbnailAlt", { name: comp.name })}
                    className="h-16 w-full rounded border border-card-border object-contain"
                  />
                ) : (
                  <div className="flex h-16 w-full items-center justify-center rounded border border-card-border bg-surface-hover">
                    <Puzzle className="h-6 w-6 text-foreground-muted" />
                  </div>
                )}
                <div className="w-full">
                  <p className="truncate text-xs font-medium text-foreground">{comp.name}</p>
                  {comp.containing_page && (
                    <p className="truncate text-xs text-foreground-muted">{comp.containing_page}</p>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleExtract}
            disabled={selectedIds.length === 0 || isExtracting}
            className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
          >
            {isExtracting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : null}
            {t("extractSelected", { count: selectedIds.length })}
          </button>
        </div>
      </div>
    );
  }

  // Step 2: Extracting
  if (step === "extracting") {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <Loader2 className="h-8 w-8 animate-spin text-interactive" />
        <p className="text-sm font-medium text-foreground">{t("extractingMessage")}</p>
        {polledImport && <StatusBadge status={polledImport.status} t={t} />}
      </div>
    );
  }

  // Step 3: Result
  return (
    <div className="flex flex-col items-center gap-4 py-6">
      {polledImport?.status === "failed" ? (
        <>
          <AlertCircle className="h-10 w-10 text-status-danger" />
          <p className="text-sm font-medium text-foreground">
            {t("conversionFailed", { error: polledImport.error_message ?? "Unknown error" })}
          </p>
          <button
            type="button"
            onClick={() => {
              setStep("select-components");
              setExtractImportId(null);
            }}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-surface-hover"
          >
            {t("tryAgain")}
          </button>
        </>
      ) : (
        <>
          <CheckCircle2 className="h-10 w-10 text-status-success" />
          <p className="text-sm font-medium text-foreground">
            {t("componentsExtracted", { count: totalComponents })}
          </p>
          <button
            type="button"
            onClick={() => router.push("/components")}
            className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
          >
            <ExternalLink className="h-4 w-4" />
            {t("viewComponents")}
          </button>
        </>
      )}
    </div>
  );
}

// ── Main Dialog ──

export function DesignImportDialog({
  open,
  onOpenChange,
  connectionId,
  connectionName,
  initialNodeIds = [],
  initialTab = "import",
}: DesignImportDialogProps) {
  const t = useTranslations("designSync");
  const [activeTab, setActiveTab] = useState<ImportTab>(initialTab);

  // Reset tab when dialog opens
  const [prevOpen, setPrevOpen] = useState(false);
  if (open && !prevOpen) {
    setActiveTab(initialTab);
  }
  if (open !== prevOpen) {
    setPrevOpen(open);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[48rem]">
        <DialogHeader>
          <DialogTitle>{t("importDialogTitle", { name: connectionName })}</DialogTitle>
          <DialogDescription className="sr-only">
            {t("importDesign")}
          </DialogDescription>
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
          <button
            type="button"
            onClick={() => setActiveTab("import")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === "import"
                ? "bg-interactive text-foreground-inverse"
                : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
            }`}
          >
            {t("tabImportDesign")}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("components")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === "components"
                ? "bg-interactive text-foreground-inverse"
                : "text-foreground-muted hover:text-foreground hover:bg-surface-hover"
            }`}
          >
            {t("tabExtractComponents")}
          </button>
        </div>

        {/* Tab content */}
        <div className="min-h-[20rem]">
          {activeTab === "import" ? (
            <ImportDesignWizard
              connectionId={connectionId}
              initialNodeIds={initialNodeIds}
              t={t}
            />
          ) : (
            <ExtractComponentsWizard
              connectionId={connectionId}
              t={t}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
