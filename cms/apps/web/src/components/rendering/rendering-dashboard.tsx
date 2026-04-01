"use client";

import { useCallback, useMemo, useState, useRef, useEffect } from "react";
import { Loader2, MonitorSmartphone, X } from "../icons";
import { useSession } from "next-auth/react";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  useScreenshotsWithConfidence,
  useCalibrationSummary,
  useTriggerCalibration,
} from "@/hooks/use-rendering-dashboard";
import { useGateEvaluate } from "@/hooks/use-rendering-gate";
import { CLIENT_DISPLAY_NAMES, CLIENT_MARKET_SHARE, type ClientProfile } from "@/types/rendering";
import { ConfidenceSummaryBar } from "./confidence-summary-bar";
import { ClientPreviewCard } from "./client-preview-card";
import { GateSummaryBadge } from "./gate-summary-badge";
import { GateClientRow } from "./gate-client-row";
import { CalibrationHealthPanel } from "./calibration-health-panel";

interface RenderingDashboardProps {
  html: string | null;
  projectId: number | null;
}

/** Identify dark variant pairs — e.g. gmail_web has gmail_web_dark */
function getDarkVariantId(clientId: string): string | null {
  const darkId = `${clientId}_dark`;
  if (darkId in CLIENT_DISPLAY_NAMES) return darkId;
  return null;
}

function isBaseClient(clientId: string): boolean {
  return !clientId.endsWith("_dark");
}

export function RenderingDashboard({ html, projectId }: RenderingDashboardProps) {
  const session = useSession();
  const isAdmin = session.data?.user?.role === "admin";

  const {
    data: screenshotData,
    trigger: triggerScreenshots,
    isMutating: screenshotsLoading,
    error: screenshotsError,
  } = useScreenshotsWithConfidence();

  const {
    data: gateResult,
    trigger: triggerGate,
    isMutating: gateLoading,
  } = useGateEvaluate();

  const {
    data: calibrationSummary,
    isLoading: calibrationLoading,
  } = useCalibrationSummary();

  const { trigger: triggerCalibration } = useTriggerCalibration();

  const handleRender = useCallback(() => {
    if (!html) return;
    triggerScreenshots({ html });
    triggerGate({ html, project_id: projectId ?? undefined });
  }, [html, projectId, triggerScreenshots, triggerGate]);

  const handleRecalibrate = useCallback(
    (clientId: string) => {
      triggerCalibration({ client_id: clientId });
    },
    [triggerCalibration],
  );

  // Full-size preview dialog state
  const [previewClientId, setPreviewClientId] = useState<string | null>(null);
  const previewDialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = previewDialogRef.current;
    if (!dialog) return;
    if (previewClientId && !dialog.open) dialog.showModal();
    if (!previewClientId && dialog.open) dialog.close();
  }, [previewClientId]);

  const handleViewFull = useCallback((clientId: string) => {
    setPreviewClientId(clientId);
  }, []);

  // -- Empty state --
  if (!html && !screenshotData) {
    return (
      <EmptyState
        icon={MonitorSmartphone}
        title="No email to preview"
        description="Select a project and build an email to see rendering previews."
      />
    );
  }

  // Build confidence data from gate results for the summary bar
  const clientResults = useMemo(
    () =>
      gateResult?.client_results.map((cr) => ({
        client_id: cr.client_name,
        score: cr.confidence_score,
        market_share:
          CLIENT_MARKET_SHARE[cr.client_name as ClientProfile] ?? 0.05,
      })) ?? [],
    [gateResult],
  );

  const overallScore = useMemo(
    () =>
      clientResults.length > 0
        ? clientResults.reduce((sum, r) => sum + r.score, 0) / clientResults.length
        : 0,
    [clientResults],
  );

  // Build screenshot lookup
  const screenshotMap = useMemo(
    () =>
      new Map(
        screenshotData?.screenshots.map((s) => [s.client_name, s.image_base64]) ?? [],
      ),
    [screenshotData],
  );

  // Only show base clients as cards (dark variants accessed via toggle)
  const baseClients = useMemo(
    () =>
      gateResult
        ? gateResult.client_results.filter((cr) => isBaseClient(cr.client_name))
        : [],
    [gateResult],
  );

  return (
    <div className="space-y-6">
      {/* Render trigger button when html is available but no data yet */}
      {html && !screenshotData && !screenshotsLoading && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleRender}
            className="rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse hover:bg-interactive-hover"
          >
            Generate Rendering Previews
          </button>
        </div>
      )}

      {/* Loading state */}
      {(screenshotsLoading || gateLoading) && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Loader2 className="h-6 w-6 animate-spin text-foreground-muted" />
          <p className="text-sm text-foreground-muted">Generating rendering previews...</p>
        </div>
      )}

      {/* Error state */}
      {screenshotsError && (
        <ErrorState
          message="Failed to generate rendering previews"
          onRetry={handleRender}
          retryLabel="Try again"
        />
      )}

      {/* Results */}
      {screenshotData && gateResult && (
        <>
          {/* 1. Confidence Summary Bar */}
          <ConfidenceSummaryBar
            clientResults={clientResults}
            overallScore={overallScore}
          />

          {/* 2. Preview Grid */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {baseClients.map((cr) => {
              const darkId = getDarkVariantId(cr.client_name);
              const displayName =
                CLIENT_DISPLAY_NAMES[cr.client_name as ClientProfile] ??
                cr.client_name;
              return (
                <ClientPreviewCard
                  key={cr.client_name}
                  clientId={cr.client_name}
                  clientName={displayName}
                  screenshot={screenshotMap.get(cr.client_name) ?? null}
                  confidence={cr.confidence_score}
                  hasDarkVariant={darkId != null}
                  darkScreenshot={
                    darkId ? (screenshotMap.get(darkId) ?? null) : null
                  }
                  onViewFull={handleViewFull}
                />
              );
            })}
          </div>

          {/* 3. Gate Status */}
          <div className="rounded-lg border border-card-border bg-card-bg p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">
                Rendering Gate
              </span>
              <GateSummaryBadge
                verdict={gateResult.verdict}
                blockingCount={gateResult.blocking_clients.length}
              />
            </div>
            <div className="space-y-1.5">
              {gateResult.client_results.map((cr) => (
                <GateClientRow key={cr.client_name} result={cr} />
              ))}
            </div>
          </div>

          {/* 4. Calibration Health (admin only) */}
          <CalibrationHealthPanel
            summary={calibrationSummary}
            isLoading={calibrationLoading}
            onRecalibrate={handleRecalibrate}
            isAdmin={isAdmin}
          />
        </>
      )}

      {/* Partial state: only screenshots, no gate (shouldn't normally happen) */}
      {screenshotData && !gateResult && !gateLoading && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {screenshotData.screenshots.map((s) => (
            <ClientPreviewCard
              key={s.client_name}
              clientId={s.client_name}
              clientName={
                CLIENT_DISPLAY_NAMES[s.client_name as ClientProfile] ??
                s.client_name
              }
              screenshot={s.image_base64}
              confidence={0}
              onViewFull={handleViewFull}
            />
          ))}
        </div>
      )}

      {/* Full-size preview dialog */}
      <dialog
        ref={previewDialogRef}
        className="w-full max-w-[28rem] rounded-lg border border-card-border bg-card-bg p-0 shadow-xl backdrop:bg-black/50"
        onClose={() => setPreviewClientId(null)}
      >
        {previewClientId && (
          <>
            <div className="flex items-center justify-between border-b border-card-border p-4">
              <h2 className="text-lg font-semibold text-foreground">
                {CLIENT_DISPLAY_NAMES[previewClientId as ClientProfile] ?? previewClientId}
              </h2>
              <button
                type="button"
                onClick={() => setPreviewClientId(null)}
                className="rounded p-1 text-foreground-muted hover:bg-surface-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-4">
              {screenshotMap.get(previewClientId) ? (
                <img
                  src={`data:image/png;base64,${screenshotMap.get(previewClientId)}`}
                  alt={`${CLIENT_DISPLAY_NAMES[previewClientId as ClientProfile] ?? previewClientId} full preview`}
                  className="w-full rounded-md border border-card-border object-contain"
                />
              ) : (
                <div className="flex aspect-[3/2] items-center justify-center rounded-md border border-card-border bg-surface-muted">
                  <p className="text-sm text-foreground-muted">No screenshot available</p>
                </div>
              )}
            </div>
          </>
        )}
      </dialog>
    </div>
  );
}
