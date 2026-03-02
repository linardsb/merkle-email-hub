"use client";

import { useCallback } from "react";
import { useTranslations } from "next-intl";
import { Download, Printer, FileSpreadsheet } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@merkle-email-hub/ui/components/ui/dropdown-menu";
import { Button } from "@merkle-email-hub/ui/components/ui/button";
import { toast } from "sonner";
import type { QADashboardMetrics } from "@/types/qa";

interface ExportReportMenuProps {
  metrics: QADashboardMetrics;
}

export function ExportReportMenu({ metrics }: ExportReportMenuProps) {
  const t = useTranslations("intelligence");

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const handleCsvExport = useCallback(() => {
    const rows: string[][] = [];

    // Section 1: Overview
    rows.push(["Rendering Intelligence Report"]);
    rows.push([`Generated: ${new Date().toLocaleDateString()}`]);
    rows.push([]);
    rows.push(["Metric", "Value"]);
    rows.push(["Total QA Runs", String(metrics.totalRuns)]);
    rows.push(["Average Score", `${Math.round(metrics.avgScore * 100)}%`]);
    rows.push(["Pass Rate", `${Math.round(metrics.passRate * 100)}%`]);
    rows.push(["Overrides", String(metrics.overrideCount)]);
    rows.push([]);

    // Section 2: Check Performance
    rows.push(["Check Performance"]);
    rows.push(["Check Name", "Average Score", "Pass Rate"]);
    for (const check of metrics.checkAverages) {
      rows.push([
        check.checkName.replace(/_/g, " "),
        `${Math.round(check.avgScore * 100)}%`,
        `${Math.round(check.passRate * 100)}%`,
      ]);
    }
    rows.push([]);

    // Section 3: Score Trend
    rows.push(["Quality Trend (Last 20 Runs)"]);
    rows.push(["Date", "Score", "Status"]);
    for (const entry of metrics.scoreTrend) {
      rows.push([
        new Date(entry.date).toLocaleDateString(),
        `${Math.round(entry.score * 100)}%`,
        entry.passed ? "Passed" : "Failed",
      ]);
    }

    // Encode CSV with proper escaping
    const csv = rows
      .map((row) =>
        row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")
      )
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `qa-intelligence-report-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success(t("exportCsvSuccess"));
  }, [metrics, t]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="no-print">
          <Download className="mr-2 h-4 w-4" />
          {t("exportReport")}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={handlePrint}>
          <Printer className="mr-2 h-4 w-4" />
          <div>
            <p>{t("exportPdf")}</p>
            <p className="text-xs text-muted-foreground">
              {t("exportPdfDescription")}
            </p>
          </div>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleCsvExport}>
          <FileSpreadsheet className="mr-2 h-4 w-4" />
          <div>
            <p>{t("exportCsv")}</p>
            <p className="text-xs text-muted-foreground">
              {t("exportCsvDescription")}
            </p>
          </div>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
