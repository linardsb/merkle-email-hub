import type { WorkflowListResponse, WorkflowStatus, ExecutionLogsResponse } from "@/types/workflows";

export const DEMO_WORKFLOWS: WorkflowListResponse = {
  flows: [
    {
      id: "email-hub.qa-pipeline",
      namespace: "email-hub",
      description: "Run full QA pipeline on a template version",
      is_template: true,
      revision: 3,
      has_schedule: false,
    },
    {
      id: "email-hub.campaign-build",
      namespace: "email-hub",
      description: "Build and deploy a campaign across all locales",
      is_template: true,
      revision: 5,
      has_schedule: false,
    },
    {
      id: "email-hub.nightly-regression",
      namespace: "email-hub",
      description: "Nightly regression tests for all golden templates",
      is_template: false,
      revision: 2,
      has_schedule: true,
    },
  ],
};

export const DEMO_EXECUTIONS: WorkflowStatus[] = [
  {
    execution_id: "exec-001",
    flow_id: "email-hub.qa-pipeline",
    status: "SUCCESS",
    started: "2026-03-18T10:00:00Z",
    ended: "2026-03-18T10:02:30Z",
    inputs: { template_version_id: 101 },
    outputs: { qa_result_id: 42, passed: true },
    task_runs: [
      { task_id: "html-validate", status: "SUCCESS", started: "2026-03-18T10:00:01Z", ended: "2026-03-18T10:00:15Z", outputs: {} },
      { task_id: "css-check", status: "SUCCESS", started: "2026-03-18T10:00:16Z", ended: "2026-03-18T10:00:45Z", outputs: {} },
      { task_id: "render-test", status: "SUCCESS", started: "2026-03-18T10:00:46Z", ended: "2026-03-18T10:02:30Z", outputs: {} },
    ],
  },
  {
    execution_id: "exec-002",
    flow_id: "email-hub.campaign-build",
    status: "RUNNING",
    started: "2026-03-18T14:00:00Z",
    ended: null,
    inputs: { project_id: 1, locales: ["en", "de", "fr"] },
    outputs: {},
    task_runs: [
      { task_id: "build-en", status: "SUCCESS", started: "2026-03-18T14:00:01Z", ended: "2026-03-18T14:01:00Z", outputs: {} },
      { task_id: "build-de", status: "RUNNING", started: "2026-03-18T14:01:01Z", ended: null, outputs: {} },
      { task_id: "build-fr", status: "CREATED", started: null, ended: null, outputs: {} },
    ],
  },
  {
    execution_id: "exec-003",
    flow_id: "email-hub.nightly-regression",
    status: "FAILED",
    started: "2026-03-17T02:00:00Z",
    ended: "2026-03-17T02:15:00Z",
    inputs: {},
    outputs: { error: "Template golden-hero-v2 failed accessibility check" },
    task_runs: [
      { task_id: "load-templates", status: "SUCCESS", started: "2026-03-17T02:00:01Z", ended: "2026-03-17T02:00:10Z", outputs: {} },
      { task_id: "run-checks", status: "FAILED", started: "2026-03-17T02:00:11Z", ended: "2026-03-17T02:15:00Z", outputs: {} },
    ],
  },
];

export const DEMO_EXECUTION_LOGS: Record<string, ExecutionLogsResponse> = {
  "exec-001": {
    execution_id: "exec-001",
    logs: [
      { timestamp: "2026-03-18T10:00:01Z", level: "INFO", message: "Starting QA pipeline for template version 101", task_id: "html-validate" },
      { timestamp: "2026-03-18T10:00:15Z", level: "INFO", message: "HTML validation passed — 0 errors, 2 warnings", task_id: "html-validate" },
      { timestamp: "2026-03-18T10:00:45Z", level: "INFO", message: "CSS support check completed — 98% compatibility", task_id: "css-check" },
      { timestamp: "2026-03-18T10:02:30Z", level: "INFO", message: "All rendering tests passed", task_id: "render-test" },
    ],
  },
  "exec-002": {
    execution_id: "exec-002",
    logs: [
      { timestamp: "2026-03-18T14:00:01Z", level: "INFO", message: "Building English locale", task_id: "build-en" },
      { timestamp: "2026-03-18T14:01:00Z", level: "INFO", message: "English build completed (42KB)", task_id: "build-en" },
      { timestamp: "2026-03-18T14:01:01Z", level: "INFO", message: "Building German locale", task_id: "build-de" },
    ],
  },
  "exec-003": {
    execution_id: "exec-003",
    logs: [
      { timestamp: "2026-03-17T02:00:01Z", level: "INFO", message: "Loading 7 golden templates", task_id: "load-templates" },
      { timestamp: "2026-03-17T02:00:11Z", level: "INFO", message: "Running regression checks...", task_id: "run-checks" },
      { timestamp: "2026-03-17T02:14:55Z", level: "ERROR", message: "Template golden-hero-v2 failed accessibility check: missing alt text on 3 images", task_id: "run-checks" },
      { timestamp: "2026-03-17T02:15:00Z", level: "ERROR", message: "Regression failed: 1 template did not pass", task_id: null },
    ],
  },
};
