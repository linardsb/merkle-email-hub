export type ReportType = "qa" | "approval" | "regression";

export interface ReportResponse {
  report_id: string;
  filename: string;
  size_bytes: number;
  generated_at: string;
  report_type: ReportType;
}

export interface ReportDownload {
  pdf_base64: string;
  filename: string;
  size_bytes: number;
  generated_at: string;
}

export interface QAReportRequest {
  qa_result_id: number;
  include_screenshots?: boolean;
  include_chaos?: boolean;
  include_deliverability?: boolean;
}

export interface ApprovalPackageRequest {
  qa_result_id: number;
  template_version_id?: number;
  include_mobile_preview?: boolean;
}

export interface RegressionReportRequest {
  entity_type: "component_version" | "golden_template";
  entity_id: number;
  baseline_test_id?: number;
  current_test_id?: number;
}
