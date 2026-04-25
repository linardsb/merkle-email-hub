"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Plug, Cloud, Palette, Mail, Loader2, CheckCircle2, XCircle } from "../icons";
import { toast } from "sonner";
import { useEmailBuild } from "@/hooks/use-email";
import { useExport } from "@/hooks/use-connectors";
import { useExportPreCheck } from "@/hooks/use-export-pre-check";
import { GatePanel } from "@/components/rendering/gate-panel";
import { ApprovalGatePanel } from "@/components/approvals/approval-gate-panel";
import { ApprovalRequestDialog } from "@/components/approvals/approval-request-dialog";
import type { ExportHistoryRecord, ConnectorPlatform } from "@/types/connectors";
import type { ExportPreCheckResponse } from "@/types/approval";

type DialogState = "idle" | "building" | "exporting" | "success" | "error";
type ConnectorTab = "raw_html" | "braze" | "sfmc" | "adobe_campaign" | "taxi";

interface ConnectorConfig {
  id: ConnectorTab;
  icon: typeof Plug;
  tabLabel: string;
  nameLabel: string;
  namePlaceholder: string;
  nameHint: string;
  exportButton: string;
  exportingMsg: string;
  successMsg: string;
  errorMsg: string;
}

const ESP_CONNECTORS: ConnectorConfig[] = [
  {
    id: "braze",
    icon: Plug,
    tabLabel: "Braze",
    nameLabel: "Content Block Name",
    namePlaceholder: "e.g., hero_block_v2",
    nameHint: "Name used in Braze to identify this content block",
    exportButton: "Export to Braze",
    exportingMsg: "Exporting to Braze\u2026",
    successMsg: "Exported to Braze successfully",
    errorMsg: "Failed to export to Braze",
  },
  {
    id: "sfmc",
    icon: Cloud,
    tabLabel: "SFMC",
    nameLabel: "Content Area Name",
    namePlaceholder: "e.g., summer_promo_2024",
    nameHint: "Name used in SFMC to identify this content area",
    exportButton: "Export to SFMC",
    exportingMsg: "Exporting to SFMC\u2026",
    successMsg: "Exported to SFMC successfully",
    errorMsg: "Failed to export to SFMC",
  },
  {
    id: "adobe_campaign",
    icon: Palette,
    tabLabel: "Adobe Campaign",
    nameLabel: "Delivery Name",
    namePlaceholder: "e.g., welcome_series_v3",
    nameHint: "Name used in Adobe Campaign for this delivery",
    exportButton: "Export to Adobe Campaign",
    exportingMsg: "Exporting to Adobe Campaign\u2026",
    successMsg: "Exported to Adobe Campaign successfully",
    errorMsg: "Failed to export to Adobe Campaign",
  },
  {
    id: "taxi",
    icon: Mail,
    tabLabel: "Taxi",
    nameLabel: "Template Name",
    namePlaceholder: "e.g., monthly_newsletter",
    nameHint: "Name used in Taxi for Email to identify this template",
    exportButton: "Export to Taxi",
    exportingMsg: "Exporting to Taxi\u2026",
    successMsg: "Exported to Taxi successfully",
    errorMsg: "Failed to export to Taxi",
  },
];

interface EspState {
  dialogState: DialogState;
  name: string;
  errorMessage: string | null;
  externalId: string | null;
}

const initialEspState: EspState = {
  dialogState: "idle",
  name: "",
  errorMessage: null,
  externalId: null,
};

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  compiledHtml: string | null;
  projectId: number;
  templateName: string;
  sourceHtml: string;
  buildId?: number | null;
  onExportComplete?: (record: ExportHistoryRecord) => void;
}

export function ExportDialog({
  open,
  onOpenChange,
  compiledHtml,
  projectId,
  templateName,
  sourceHtml,
  buildId,
  onExportComplete,
}: ExportDialogProps) {
  const [activeTab, setActiveTab] = useState<ConnectorTab>("raw_html");
  const [espStates, setEspStates] = useState<Record<string, EspState>>({});
  const [showGate, setShowGate] = useState(false);
  const [pendingExportCfg, setPendingExportCfg] = useState<ConnectorConfig | null>(null);
  const [preCheckResult, setPreCheckResult] = useState<ExportPreCheckResponse | null>(null);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const { trigger: triggerBuild } = useEmailBuild();
  const { trigger: triggerExport } = useExport();
  const { trigger: triggerPreCheck } = useExportPreCheck();

  const espStatesRef = useRef(espStates);
  espStatesRef.current = espStates;

  const getEspState = (id: string): EspState => espStates[id] ?? initialEspState;

  const updateEspState = useCallback((id: string, patch: Partial<EspState>) => {
    setEspStates((prev) => ({
      ...prev,
      [id]: { ...(prev[id] ?? initialEspState), ...patch },
    }));
  }, []);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setEspStates({});
      setShowGate(false);
      setPendingExportCfg(null);
      setPreCheckResult(null);
      setApprovalDialogOpen(false);
    }
  }, [open]);

  // Sync dialog open/close
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const handleDialogClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDialogElement>) => {
      if (e.target === dialogRef.current) {
        onOpenChange(false);
      }
    },
    [onOpenChange],
  );

  const handleRawHtmlDownload = useCallback(() => {
    if (!compiledHtml) return;

    const blob = new Blob([compiledHtml], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${templateName.replace(/\s+/g, "_").toLowerCase()}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success("HTML file downloaded");

    onExportComplete?.({
      local_id: crypto.randomUUID(),
      platform: "raw_html",
      name: templateName,
      status: "success",
      error_message: null,
      external_id: null,
      created_at: new Date().toISOString(),
      build_id: null,
    });
  }, [compiledHtml, templateName, onExportComplete]);

  const handleEspExport = useCallback(
    async (cfg: ConnectorConfig) => {
      const state = espStatesRef.current[cfg.id] ?? initialEspState;
      if (
        !state.name.trim() ||
        state.dialogState === "building" ||
        state.dialogState === "exporting"
      )
        return;

      const localId = crypto.randomUUID();
      updateEspState(cfg.id, { dialogState: "building", errorMessage: null, externalId: null });

      onExportComplete?.({
        local_id: localId,
        platform: cfg.id as ConnectorPlatform,
        name: state.name,
        status: "exporting",
        error_message: null,
        external_id: null,
        created_at: new Date().toISOString(),
        build_id: null,
      });

      try {
        // Step 1: Build production version
        const buildResult = await triggerBuild({
          project_id: projectId,
          template_name: templateName,
          source_html: sourceHtml,
          is_production: true,
        });

        if (!buildResult?.id) {
          throw new Error("Build failed — no build ID returned");
        }

        // Step 2: Export to connector
        updateEspState(cfg.id, { dialogState: "exporting" });
        const exportResult = await triggerExport({
          build_id: buildResult.id,
          connector_type: cfg.id,
          content_block_name: state.name.trim(),
        });

        updateEspState(cfg.id, {
          dialogState: "success",
          externalId: exportResult?.external_id ?? null,
        });
        toast.success(cfg.successMsg);

        onExportComplete?.({
          local_id: localId,
          platform: cfg.id as ConnectorPlatform,
          name: state.name,
          status: "success",
          error_message: null,
          external_id: exportResult?.external_id ?? null,
          created_at: new Date().toISOString(),
          build_id: buildResult.id,
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : cfg.errorMsg;
        updateEspState(cfg.id, { dialogState: "error", errorMessage: message });
        toast.error(cfg.errorMsg);

        onExportComplete?.({
          local_id: localId,
          platform: cfg.id as ConnectorPlatform,
          name: state.name,
          status: "failed",
          error_message: message,
          external_id: null,
          created_at: new Date().toISOString(),
          build_id: null,
        });
      }
    },

    [
      projectId,
      templateName,
      sourceHtml,
      triggerBuild,
      triggerExport,
      onExportComplete,
      updateEspState,
    ],
  );

  const handleEspExportClick = useCallback(
    async (cfg: ConnectorConfig) => {
      const state = espStatesRef.current[cfg.id] ?? initialEspState;
      if (!state.name.trim() || !compiledHtml) return;
      setPendingExportCfg(cfg);

      // Run pre-check to determine if approval is needed
      try {
        const result = await triggerPreCheck({
          html: compiledHtml,
          project_id: projectId,
          ...(buildId ? { build_id: buildId } : {}),
        });
        setPreCheckResult(result);

        if (result.approval?.required && !result.approval.passed) {
          // Show gate panel area — approval gate will block
          setShowGate(true);
          return;
        }
      } catch {
        // Pre-check failed — proceed to rendering gate only
      }

      setShowGate(true);
    },
    [compiledHtml, projectId, buildId, triggerPreCheck],
  );

  const handleGateApproved = useCallback(() => {
    // Block if approval is required but not passed
    if (preCheckResult?.approval?.required && !preCheckResult.approval.passed) {
      toast.warning("Approval required before export");
      return;
    }
    setShowGate(false);
    if (pendingExportCfg) {
      handleEspExport(pendingExportCfg);
    }
  }, [pendingExportCfg, handleEspExport, preCheckResult]);

  if (!open) return null;

  const activeConfig = ESP_CONNECTORS.find((c) => c.id === activeTab);

  return (
    <dialog
      ref={dialogRef}
      onClose={handleDialogClose}
      onClick={handleBackdropClick}
      className="border-card-border bg-card-bg fixed inset-0 z-50 m-auto max-h-[85vh] w-full max-w-[36rem] rounded-lg border p-0 shadow-lg backdrop:bg-black/50"
    >
      <div className="flex flex-col">
        {/* Header */}
        <div className="border-card-border border-b px-6 py-4">
          <h2 className="text-foreground text-lg font-semibold">{"Export Template"}</h2>
        </div>

        {/* Tabs */}
        <div className="border-card-border flex overflow-x-auto border-b px-6">
          <button
            type="button"
            onClick={() => setActiveTab("raw_html")}
            className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "raw_html"
                ? "border-interactive text-foreground"
                : "text-foreground-muted hover:text-foreground border-transparent"
            }`}
          >
            <Download className="h-4 w-4" />
            {"Raw HTML"}
          </button>
          {ESP_CONNECTORS.map((cfg) => (
            <button
              key={cfg.id}
              type="button"
              onClick={() => setActiveTab(cfg.id)}
              className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                activeTab === cfg.id
                  ? "border-interactive text-foreground"
                  : "text-foreground-muted hover:text-foreground border-transparent"
              }`}
            >
              <cfg.icon className="h-4 w-4" />
              {cfg.tabLabel}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="px-6 py-5">
          {activeTab === "raw_html" ? (
            <div className="space-y-4">
              {!compiledHtml ? (
                <p className="text-foreground-muted text-sm">
                  {"Compile the template first before exporting"}
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleRawHtmlDownload}
                  className="bg-interactive text-foreground-inverse hover:bg-interactive-hover flex w-full items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors"
                >
                  <Download className="h-4 w-4" />
                  {"Download HTML"}
                </button>
              )}
            </div>
          ) : activeConfig ? (
            showGate && pendingExportCfg?.id === activeConfig.id ? (
              <div className="space-y-4">
                {preCheckResult?.approval?.required && (
                  <ApprovalGatePanel
                    approvalResult={preCheckResult.approval}
                    onRequestApproval={() => setApprovalDialogOpen(true)}
                  />
                )}
                <GatePanel
                  html={compiledHtml}
                  projectId={projectId}
                  onApproved={handleGateApproved}
                  onCancel={() => setShowGate(false)}
                  approveLabel={pendingExportCfg.exportButton}
                />
              </div>
            ) : (
              <EspTabContent
                config={activeConfig}
                state={getEspState(activeConfig.id)}
                compiledHtml={compiledHtml}
                onNameChange={(val) => updateEspState(activeConfig.id, { name: val })}
                onExport={() => handleEspExportClick(activeConfig)}
                onRetry={() =>
                  updateEspState(activeConfig.id, { dialogState: "idle", errorMessage: null })
                }
              />
            )
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-card-border border-t px-6 py-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="text-foreground-muted hover:text-foreground rounded-md px-4 py-2 text-sm font-medium transition-colors"
          >
            {"Close"}
          </button>
        </div>
      </div>

      <ApprovalRequestDialog
        open={approvalDialogOpen}
        onOpenChange={setApprovalDialogOpen}
        buildId={buildId ?? null}
        projectId={projectId}
        compiledHtml={compiledHtml}
        onSubmitted={() => {
          setApprovalDialogOpen(false);
          toast.success("Approval request submitted — export will be available after review");
        }}
      />
    </dialog>
  );
}

function EspTabContent({
  config,
  state,
  compiledHtml,
  onNameChange,
  onExport,
  onRetry,
}: {
  config: ConnectorConfig;
  state: EspState;
  compiledHtml: string | null;
  onNameChange: (val: string) => void;
  onExport: () => void;
  onRetry: () => void;
}) {
  const isNameValid = state.name.trim().length >= 1 && state.name.trim().length <= 200;
  const isBusy = state.dialogState === "building" || state.dialogState === "exporting";

  return (
    <div className="space-y-4">
      {/* Name Input */}
      <div>
        <label
          htmlFor={`${config.id}-name`}
          className="text-foreground mb-1.5 block text-sm font-medium"
        >
          {config.nameLabel}
        </label>
        <input
          id={`${config.id}-name`}
          type="text"
          value={state.name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={config.namePlaceholder}
          maxLength={200}
          disabled={isBusy}
          className="border-input-border bg-input-bg text-foreground placeholder:text-foreground-muted focus:border-interactive focus:ring-interactive w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-1 disabled:opacity-50"
        />
        <p className="text-foreground-muted mt-1 text-xs">{config.nameHint}</p>
      </div>

      {/* State-based UI */}
      {state.dialogState === "building" && (
        <div className="text-foreground-muted flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {"Building production version…"}
        </div>
      )}

      {state.dialogState === "exporting" && (
        <div className="text-foreground-muted flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          {config.exportingMsg}
        </div>
      )}

      {state.dialogState === "success" && (
        <div className="border-status-success/20 bg-status-success/5 rounded-md border p-3">
          <div className="text-status-success flex items-center gap-2 text-sm font-medium">
            <CheckCircle2 className="h-4 w-4" />
            {config.successMsg}
          </div>
          {state.externalId && (
            <p className="text-foreground-muted mt-1 text-xs">
              {"External ID"}: {state.externalId}
            </p>
          )}
        </div>
      )}

      {state.dialogState === "error" && (
        <div className="space-y-2">
          <div className="border-status-danger/20 bg-status-danger/5 rounded-md border p-3">
            <div className="text-status-danger flex items-center gap-2 text-sm font-medium">
              <XCircle className="h-4 w-4" />
              {state.errorMessage ?? config.errorMsg}
            </div>
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="text-interactive text-sm font-medium hover:underline"
          >
            {"Retry"}
          </button>
        </div>
      )}

      {/* Export Button */}
      {(state.dialogState === "idle" || state.dialogState === "error") && (
        <button
          type="button"
          onClick={onExport}
          disabled={!isNameValid || !compiledHtml}
          className="bg-interactive text-foreground-inverse hover:bg-interactive-hover flex w-full items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
        >
          <config.icon className="h-4 w-4" />
          {config.exportButton}
        </button>
      )}

      {!compiledHtml && state.dialogState === "idle" && (
        <p className="text-foreground-muted text-xs">
          {"Compile the template first before exporting"}
        </p>
      )}
    </div>
  );
}
