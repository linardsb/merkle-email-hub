"use client";

import { useState, useEffect, useCallback } from "react";
import { Download, Eye, FileText, Plus } from "../icons";
import {
  useGenerateQAReport,
  useGenerateApprovalReport,
  useGenerateRegressionReport,
  useReportDownload,
} from "@/hooks/use-reports";
import type { ReportResponse, ReportType } from "@/types/reports";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";

const STORAGE_KEY = "ecosystem-report-history";

function loadReportHistory(): ReportResponse[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (r): r is ReportResponse =>
        typeof r === "object" && r !== null && "report_id" in r && "filename" in r,
    );
  } catch {
    return [];
  }
}

function saveReportHistory(reports: ReportResponse[]) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(reports));
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const TYPE_COLORS: Record<ReportType, string> = {
  qa: "bg-status-info/10 text-status-info",
  approval: "bg-status-success/10 text-status-success",
  regression: "bg-status-warning/10 text-status-warning",
};

export function ReportPanel() {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewReportId, setPreviewReportId] = useState<string | null>(null);
  const [reportType, setReportType] = useState<ReportType>("qa");

  // Form fields
  const [qaResultId, setQaResultId] = useState("");
  const [includeScreenshots, setIncludeScreenshots] = useState(false);
  const [includeChaos, setIncludeChaos] = useState(false);
  const [includeDeliverability, setIncludeDeliverability] = useState(false);
  const [templateVersionId, setTemplateVersionId] = useState("");
  const [includeMobilePreview, setIncludeMobilePreview] = useState(false);
  const [entityType, setEntityType] = useState<"component_version" | "golden_template">("component_version");
  const [entityId, setEntityId] = useState("");

  const { trigger: genQA, isMutating: genQALoading } = useGenerateQAReport();
  const { trigger: genApproval, isMutating: genApprovalLoading } = useGenerateApprovalReport();
  const { trigger: genRegression, isMutating: genRegressionLoading } = useGenerateRegressionReport();
  const { trigger: downloadReport } = useReportDownload(previewReportId);

  const isGenerating = genQALoading || genApprovalLoading || genRegressionLoading;

  useEffect(() => {
    setReports(loadReportHistory());
  }, []);

  const addReport = useCallback((report: ReportResponse) => {
    setReports((prev) => {
      const next = [report, ...prev];
      saveReportHistory(next);
      return next;
    });
  }, []);

  async function handleGenerate() {
    let result: ReportResponse | undefined;
    if (reportType === "qa") {
      result = await genQA({
        qa_result_id: parseInt(qaResultId, 10) || 1,
        include_screenshots: includeScreenshots,
        include_chaos: includeChaos,
        include_deliverability: includeDeliverability,
      });
    } else if (reportType === "approval") {
      result = await genApproval({
        qa_result_id: parseInt(qaResultId, 10) || 1,
        template_version_id: templateVersionId ? parseInt(templateVersionId, 10) : undefined,
        include_mobile_preview: includeMobilePreview,
      });
    } else {
      result = await genRegression({
        entity_type: entityType,
        entity_id: parseInt(entityId, 10) || 1,
      });
    }
    if (result) {
      addReport(result);
      setGenerateOpen(false);
    }
  }

  async function handleDownload(reportId: string, filename: string) {
    const data = await downloadReport();
    if (!data) return;
    try {
      const bytes = Uint8Array.from(atob(data.pdf_base64), (c) => c.charCodeAt(0));
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Download failed silently
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-foreground-muted">
          {reports.length} report{reports.length !== 1 ? "s" : ""} generated this session
        </p>
        <button
          onClick={() => setGenerateOpen(true)}
          className="flex items-center gap-1.5 rounded-md bg-interactive px-3 py-1.5 text-sm font-medium text-foreground-inverse hover:bg-interactive-hover"
        >
          <Plus className="h-4 w-4" /> Generate Report
        </button>
      </div>

      {/* Report History */}
      {reports.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-card-border bg-card-bg py-12">
          <FileText className="h-10 w-10 text-foreground-muted" />
          <p className="text-foreground-muted">No reports yet. Generate your first report above.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-card-border">
          <table className="w-full text-sm">
            <thead className="bg-card-bg text-left text-foreground-muted">
              <tr>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Filename</th>
                <th className="px-4 py-2 font-medium">Size</th>
                <th className="px-4 py-2 font-medium">Generated</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-card-border">
              {reports.map((r) => (
                <tr key={r.report_id} className="hover:bg-surface-hover">
                  <td className="px-4 py-2.5">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${TYPE_COLORS[r.report_type]}`}>
                      {r.report_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{r.filename}</td>
                  <td className="px-4 py-2.5 text-foreground-muted">{formatBytes(r.size_bytes)}</td>
                  <td className="px-4 py-2.5 text-foreground-muted">{relativeTime(r.generated_at)}</td>
                  <td className="flex gap-1.5 px-4 py-2.5">
                    <button
                      onClick={() => {
                        setPreviewReportId(r.report_id);
                        setPreviewOpen(true);
                      }}
                      className="rounded-md border border-card-border p-1.5 text-foreground-muted hover:bg-surface-hover"
                      title="Preview"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDownload(r.report_id, r.filename)}
                      className="rounded-md border border-card-border p-1.5 text-foreground-muted hover:bg-surface-hover"
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Generate Dialog */}
      <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
        <DialogContent className="sm:max-w-[32rem]">
          <DialogHeader>
            <DialogTitle>Generate Report</DialogTitle>
            <DialogDescription>Select the report type and configure options.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {/* Type Selector */}
            <div className="flex gap-1 rounded-lg border border-card-border bg-card-bg p-1">
              {(["qa", "approval", "regression"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setReportType(t)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                    reportType === t
                      ? "bg-interactive text-foreground-inverse"
                      : "text-foreground-muted hover:bg-surface-hover hover:text-foreground"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* QA fields */}
            {reportType === "qa" && (
              <>
                <div>
                  <label className="mb-1 block text-sm font-medium">QA Result ID</label>
                  <input
                    type="number"
                    value={qaResultId}
                    onChange={(e) => setQaResultId(e.target.value)}
                    placeholder="e.g. 42"
                    className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeScreenshots} onChange={(e) => setIncludeScreenshots(e.target.checked)} />
                    Include screenshots
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeChaos} onChange={(e) => setIncludeChaos(e.target.checked)} />
                    Include chaos testing
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={includeDeliverability} onChange={(e) => setIncludeDeliverability(e.target.checked)} />
                    Include deliverability
                  </label>
                </div>
              </>
            )}

            {/* Approval fields */}
            {reportType === "approval" && (
              <>
                <div>
                  <label className="mb-1 block text-sm font-medium">QA Result ID</label>
                  <input
                    type="number"
                    value={qaResultId}
                    onChange={(e) => setQaResultId(e.target.value)}
                    placeholder="e.g. 42"
                    className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Template Version ID (optional)</label>
                  <input
                    type="number"
                    value={templateVersionId}
                    onChange={(e) => setTemplateVersionId(e.target.value)}
                    className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={includeMobilePreview} onChange={(e) => setIncludeMobilePreview(e.target.checked)} />
                  Include mobile preview
                </label>
              </>
            )}

            {/* Regression fields */}
            {reportType === "regression" && (
              <>
                <div>
                  <label className="mb-1 block text-sm font-medium">Entity Type</label>
                  <select
                    value={entityType}
                    onChange={(e) => setEntityType(e.target.value as "component_version" | "golden_template")}
                    className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm"
                  >
                    <option value="component_version">Component Version</option>
                    <option value="golden_template">Golden Template</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Entity ID</label>
                  <input
                    type="number"
                    value={entityId}
                    onChange={(e) => setEntityId(e.target.value)}
                    placeholder="e.g. 1"
                    className="w-full rounded-md border border-input-border bg-input-bg px-3 py-2 text-sm"
                  />
                </div>
              </>
            )}

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full rounded-md bg-interactive px-4 py-2 text-sm font-medium text-foreground-inverse hover:bg-interactive-hover disabled:opacity-50"
            >
              {isGenerating ? "Generating…" : "Generate"}
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Report Preview</DialogTitle>
            <DialogDescription>PDF preview for report {previewReportId}</DialogDescription>
          </DialogHeader>
          <div className="pt-2">
            <iframe
              src={`data:application/pdf;base64,`}
              sandbox=""
              className="h-[80vh] w-full rounded border border-card-border"
              title="Report Preview"
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
