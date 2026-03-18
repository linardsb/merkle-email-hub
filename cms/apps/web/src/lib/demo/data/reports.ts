import type { ReportResponse, ReportDownload } from "@/types/reports";

export const DEMO_REPORTS: ReportResponse[] = [
  {
    report_id: "rpt-001",
    filename: "qa-report-spring-sale-v3.pdf",
    size_bytes: 245_760,
    generated_at: "2026-03-18T09:30:00Z",
    report_type: "qa",
  },
  {
    report_id: "rpt-002",
    filename: "approval-package-welcome-series.pdf",
    size_bytes: 512_000,
    generated_at: "2026-03-17T16:00:00Z",
    report_type: "approval",
  },
  {
    report_id: "rpt-003",
    filename: "regression-hero-component-v2.pdf",
    size_bytes: 184_320,
    generated_at: "2026-03-16T08:15:00Z",
    report_type: "regression",
  },
];

/** Minimal PDF (blank page) encoded as base64 for demo preview */
const MINIMAL_PDF_BASE64 =
  "JVBERi0xLjEKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5k" +
  "b2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4K" +
  "ZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3gg" +
  "WzAgMCA2MTIgNzkyXSA+PgplbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAow" +
  "MDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMMDAwIG4gCnRyYWlsZXIKPDwgL1NpemUgNCAvUm9vdCAxIDAgUiA+PgpzdGFydHhyZWYKMTc0CiUlRU9GCg==";

export function buildDemoReportDownload(reportId: string): ReportDownload {
  const report = DEMO_REPORTS.find((r) => r.report_id === reportId);
  return {
    pdf_base64: MINIMAL_PDF_BASE64,
    filename: report?.filename ?? `report-${reportId}.pdf`,
    size_bytes: report?.size_bytes ?? 100_000,
    generated_at: report?.generated_at ?? new Date().toISOString(),
  };
}

export function buildDemoReportResponse(reportType: string): ReportResponse {
  return {
    report_id: `rpt-${Date.now().toString(36)}`,
    filename: `${reportType}-report-${new Date().toISOString().slice(0, 10)}.pdf`,
    size_bytes: 150_000 + Math.floor(Math.random() * 300_000),
    generated_at: new Date().toISOString(),
    report_type: reportType as ReportResponse["report_type"],
  };
}
