"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Download, Plug, Cloud, Palette, Mail, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { useEmailBuild } from "@/hooks/use-email";
import { useExport } from "@/hooks/use-connectors";
import type { ExportHistoryRecord, ConnectorPlatform } from "@/types/connectors";

type DialogState = "idle" | "building" | "exporting" | "success" | "error";
type ConnectorTab = "raw_html" | "braze" | "sfmc" | "adobe_campaign" | "taxi";

interface ConnectorConfig {
  id: ConnectorTab;
  icon: typeof Plug;
  tabKey: string;
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
    tabKey: "tabBraze",
    nameLabel: "brazeContentBlockName",
    namePlaceholder: "brazeContentBlockPlaceholder",
    nameHint: "brazeContentBlockHint",
    exportButton: "exportToBraze",
    exportingMsg: "exporting",
    successMsg: "brazeExportSuccess",
    errorMsg: "brazeExportError",
  },
  {
    id: "sfmc",
    icon: Cloud,
    tabKey: "tabSfmc",
    nameLabel: "sfmcContentAreaName",
    namePlaceholder: "sfmcContentAreaPlaceholder",
    nameHint: "sfmcContentAreaHint",
    exportButton: "exportToSfmc",
    exportingMsg: "sfmcExporting",
    successMsg: "sfmcExportSuccess",
    errorMsg: "sfmcExportError",
  },
  {
    id: "adobe_campaign",
    icon: Palette,
    tabKey: "tabAdobeCampaign",
    nameLabel: "adobeDeliveryName",
    namePlaceholder: "adobeDeliveryPlaceholder",
    nameHint: "adobeDeliveryHint",
    exportButton: "exportToAdobe",
    exportingMsg: "adobeExporting",
    successMsg: "adobeExportSuccess",
    errorMsg: "adobeExportError",
  },
  {
    id: "taxi",
    icon: Mail,
    tabKey: "tabTaxi",
    nameLabel: "taxiTemplateName",
    namePlaceholder: "taxiTemplatePlaceholder",
    nameHint: "taxiTemplateHint",
    exportButton: "exportToTaxi",
    exportingMsg: "taxiExporting",
    successMsg: "taxiExportSuccess",
    errorMsg: "taxiExportError",
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
  onExportComplete?: (record: ExportHistoryRecord) => void;
}

export function ExportDialog({
  open,
  onOpenChange,
  compiledHtml,
  projectId,
  templateName,
  sourceHtml,
  onExportComplete,
}: ExportDialogProps) {
  const t = useTranslations("export");
  const [activeTab, setActiveTab] = useState<ConnectorTab>("raw_html");
  const [espStates, setEspStates] = useState<Record<string, EspState>>({});
  const dialogRef = useRef<HTMLDialogElement>(null);

  const { trigger: triggerBuild } = useEmailBuild();
  const { trigger: triggerExport } = useExport();

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
    [onOpenChange]
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

    toast.success(t("downloadSuccess"));

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
  }, [compiledHtml, templateName, t, onExportComplete]);

  const handleEspExport = useCallback(
    async (cfg: ConnectorConfig) => {
      const state = getEspState(cfg.id);
      if (!state.name.trim() || state.dialogState === "building" || state.dialogState === "exporting") return;

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
        toast.success(t(cfg.successMsg));

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
        const message = err instanceof Error ? err.message : t(cfg.errorMsg);
        updateEspState(cfg.id, { dialogState: "error", errorMessage: message });
        toast.error(t(cfg.errorMsg));

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [espStates, projectId, templateName, sourceHtml, triggerBuild, triggerExport, t, onExportComplete, updateEspState]
  );

  if (!open) return null;

  const activeConfig = ESP_CONNECTORS.find((c) => c.id === activeTab);

  return (
    <dialog
      ref={dialogRef}
      onClose={handleDialogClose}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 m-auto max-h-[85vh] w-full max-w-[36rem] rounded-lg border border-card-border bg-card-bg p-0 shadow-lg backdrop:bg-black/50"
    >
      <div className="flex flex-col">
        {/* Header */}
        <div className="border-b border-card-border px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">{t("title")}</h2>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-card-border px-6 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab("raw_html")}
            className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "raw_html"
                ? "border-interactive text-foreground"
                : "border-transparent text-foreground-muted hover:text-foreground"
            }`}
          >
            <Download className="h-4 w-4" />
            {t("tabRawHtml")}
          </button>
          {ESP_CONNECTORS.map((cfg) => (
            <button
              key={cfg.id}
              type="button"
              onClick={() => setActiveTab(cfg.id)}
              className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                activeTab === cfg.id
                  ? "border-interactive text-foreground"
                  : "border-transparent text-foreground-muted hover:text-foreground"
              }`}
            >
              <cfg.icon className="h-4 w-4" />
              {t(cfg.tabKey)}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="px-6 py-5">
          {activeTab === "raw_html" ? (
            <div className="space-y-4">
              {!compiledHtml ? (
                <p className="text-sm text-foreground-muted">
                  {t("noCompiledHtml")}
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleRawHtmlDownload}
                  className="flex w-full items-center justify-center gap-2 rounded-md bg-interactive px-4 py-2.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover"
                >
                  <Download className="h-4 w-4" />
                  {t("downloadHtml")}
                </button>
              )}
            </div>
          ) : activeConfig ? (
            <EspTabContent
              config={activeConfig}
              state={getEspState(activeConfig.id)}
              compiledHtml={compiledHtml}
              onNameChange={(val) => updateEspState(activeConfig.id, { name: val })}
              onExport={() => handleEspExport(activeConfig)}
              onRetry={() => updateEspState(activeConfig.id, { dialogState: "idle", errorMessage: null })}
              t={t}
            />
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t border-card-border px-6 py-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-md px-4 py-2 text-sm font-medium text-foreground-muted transition-colors hover:text-foreground"
          >
            {t("close")}
          </button>
        </div>
      </div>
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
  t,
}: {
  config: ConnectorConfig;
  state: EspState;
  compiledHtml: string | null;
  onNameChange: (val: string) => void;
  onExport: () => void;
  onRetry: () => void;
  t: ReturnType<typeof useTranslations<"export">>;
}) {
  const isNameValid = state.name.trim().length >= 1 && state.name.trim().length <= 200;
  const isBusy = state.dialogState === "building" || state.dialogState === "exporting";

  return (
    <div className="space-y-4">
      {/* Name Input */}
      <div>
        <label
          htmlFor={`${config.id}-name`}
          className="mb-1.5 block text-sm font-medium text-foreground"
        >
          {t(config.nameLabel)}
        </label>
        <input
          id={`${config.id}-name`}
          type="text"
          value={state.name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={t(config.namePlaceholder)}
          maxLength={200}
          disabled={isBusy}
          className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:border-interactive focus:outline-none focus:ring-1 focus:ring-interactive disabled:opacity-50"
        />
        <p className="mt-1 text-xs text-foreground-muted">
          {t(config.nameHint)}
        </p>
      </div>

      {/* State-based UI */}
      {state.dialogState === "building" && (
        <div className="flex items-center gap-2 text-sm text-foreground-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("building")}
        </div>
      )}

      {state.dialogState === "exporting" && (
        <div className="flex items-center gap-2 text-sm text-foreground-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t(config.exportingMsg)}
        </div>
      )}

      {state.dialogState === "success" && (
        <div className="rounded-md border border-status-success/20 bg-status-success/5 p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-status-success">
            <CheckCircle2 className="h-4 w-4" />
            {t(config.successMsg)}
          </div>
          {state.externalId && (
            <p className="mt-1 text-xs text-foreground-muted">
              {t("externalId")}: {state.externalId}
            </p>
          )}
        </div>
      )}

      {state.dialogState === "error" && (
        <div className="space-y-2">
          <div className="rounded-md border border-status-danger/20 bg-status-danger/5 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-status-danger">
              <XCircle className="h-4 w-4" />
              {state.errorMessage ?? t(config.errorMsg)}
            </div>
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="text-sm font-medium text-interactive hover:underline"
          >
            {t("retry")}
          </button>
        </div>
      )}

      {/* Export Button */}
      {(state.dialogState === "idle" || state.dialogState === "error") && (
        <button
          type="button"
          onClick={onExport}
          disabled={!isNameValid || !compiledHtml}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-interactive px-4 py-2.5 text-sm font-medium text-foreground-inverse transition-colors hover:bg-interactive-hover disabled:opacity-50"
        >
          <config.icon className="h-4 w-4" />
          {t(config.exportButton)}
        </button>
      )}

      {!compiledHtml && state.dialogState === "idle" && (
        <p className="text-xs text-foreground-muted">
          {t("noCompiledHtml")}
        </p>
      )}
    </div>
  );
}
