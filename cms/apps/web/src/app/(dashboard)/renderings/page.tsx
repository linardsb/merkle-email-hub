"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { MonitorSmartphone } from "lucide-react";
import { Skeleton } from "@merkle-email-hub/ui/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useRenderingClients, useRenderingTests } from "@/hooks/use-renderings";
import { RenderingStatsCards } from "@/components/renderings/rendering-stats-cards";
import { ClientCompatibilityMatrix } from "@/components/renderings/client-compatibility-matrix";
import { RenderingTestList } from "@/components/renderings/rendering-test-list";
import { RenderingTestDialog } from "@/components/renderings/rendering-test-dialog";
import { RenderingScreenshotDialog } from "@/components/renderings/rendering-screenshot-dialog";
import type { RenderingResult } from "@/types/rendering";

export default function RenderingsPage() {
  const t = useTranslations("renderings");

  const { data: clients, isLoading: clientsLoading, error: clientsError } = useRenderingClients();
  const { data: testsData, isLoading: testsLoading, error: testsError, mutate } = useRenderingTests({ pageSize: 10 });

  const [dialogOpen, setDialogOpen] = useState(false);
  const [screenshotResult, setScreenshotResult] = useState<RenderingResult | null>(null);
  const [screenshotClientName, setScreenshotClientName] = useState("");
  const [screenshotOpen, setScreenshotOpen] = useState(false);

  const handleScreenshotClick = useCallback((result: RenderingResult, clientName: string) => {
    setScreenshotResult(result);
    setScreenshotClientName(clientName);
    setScreenshotOpen(true);
  }, []);

  const isLoading = clientsLoading || testsLoading;
  const error = clientsError || testsError;
  const tests = testsData?.items ?? [];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg border border-card-border" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-lg border border-card-border" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
        </div>
        <ErrorState message={t("error")} onRetry={() => mutate()} retryLabel={t("retry")} />
      </div>
    );
  }

  if (tests.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
              <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
            </div>
          </div>
          <button
            onClick={() => setDialogOpen(true)}
            className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            {t("requestTest")}
          </button>
        </div>
        <EmptyState
          icon={MonitorSmartphone}
          title={t("noTests")}
          description={t("noTestsDescription")}
        />
        <RenderingTestDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          onTestComplete={() => mutate()}
        />
      </div>
    );
  }

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MonitorSmartphone className="h-8 w-8 text-foreground-accent" />
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-foreground-muted">{t("subtitle")}</p>
          </div>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="rounded bg-foreground-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          {t("requestTest")}
        </button>
      </div>

      {/* Stats */}
      <RenderingStatsCards tests={tests} />

      {/* Compatibility Matrix */}
      {clients && <ClientCompatibilityMatrix clients={clients} tests={tests} />}

      {/* Test List */}
      <RenderingTestList tests={tests} onScreenshotClick={handleScreenshotClick} />

      {/* Dialogs */}
      <RenderingTestDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onTestComplete={() => mutate()}
      />
      <RenderingScreenshotDialog
        open={screenshotOpen}
        onOpenChange={setScreenshotOpen}
        result={screenshotResult}
        clientName={screenshotClientName}
      />
    </div>
  );
}
