"use client";

import { useState } from "react";
import { Play, ChevronDown, ChevronRight, Clock, AlertCircle } from "../icons";
import {
  useWorkflows,
  useWorkflowStatus,
  useWorkflowLogs,
  useTriggerWorkflow,
} from "@/hooks/use-workflows";
import type { WorkflowExecutionStatus, WorkflowStatus as WFStatus } from "@/types/workflows";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@email-hub/ui/components/ui/dialog";

const STATUS_COLORS: Record<WorkflowExecutionStatus, string> = {
  CREATED: "bg-foreground-muted",
  RUNNING: "bg-status-info",
  SUCCESS: "bg-status-success",
  FAILED: "bg-status-error",
  WARNING: "bg-status-warning",
  PAUSED: "bg-foreground-muted",
  KILLED: "bg-status-error",
};

const STATUS_TEXT_COLORS: Record<WorkflowExecutionStatus, string> = {
  CREATED: "text-foreground-muted",
  RUNNING: "text-status-info",
  SUCCESS: "text-status-success",
  FAILED: "text-status-error",
  WARNING: "text-status-warning",
  PAUSED: "text-foreground-muted",
  KILLED: "text-status-error",
};

export function WorkflowPanel() {
  const { data: workflowData, isLoading } = useWorkflows();
  const { trigger: triggerWorkflow, isMutating: triggering } = useTriggerWorkflow();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedFlowId, setSelectedFlowId] = useState("");
  const [inputsJson, setInputsJson] = useState("{}");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [executions, setExecutions] = useState<WFStatus[]>([]);
  const [expandedExecId, setExpandedExecId] = useState<string | null>(null);
  const [activeExecId, setActiveExecId] = useState<string | null>(null);

  const flows = workflowData?.flows ?? [];

  // Poll active execution
  const isActive = executions.some((e) => e.status === "RUNNING" || e.status === "CREATED");
  const { data: polledStatus } = useWorkflowStatus(activeExecId, isActive);
  const { data: logs } = useWorkflowLogs(expandedExecId);

  // Merge polled status into executions
  if (polledStatus && activeExecId) {
    const idx = executions.findIndex((e) => e.execution_id === activeExecId);
    if (idx >= 0 && executions[idx]!.status !== polledStatus.status) {
      executions[idx] = polledStatus;
    }
  }

  async function handleTrigger() {
    setJsonError(null);
    let parsed: Record<string, unknown> = {};
    try {
      parsed = JSON.parse(inputsJson);
    } catch {
      setJsonError("Invalid JSON");
      return;
    }

    const result = await triggerWorkflow({
      flow_id: selectedFlowId,
      inputs: parsed,
    });
    if (result) {
      setExecutions((prev) => [result, ...prev]);
      setActiveExecId(result.execution_id);
    }
    setDialogOpen(false);
    setInputsJson("{}");
  }

  function formatDuration(started: string, ended: string | null): string {
    const start = new Date(started).getTime();
    const end = ended ? new Date(ended).getTime() : Date.now();
    const seconds = Math.round((end - start) / 1000);
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }

  return (
    <div className="space-y-6">
      {/* Available Flows */}
      <section>
        <h3 className="text-foreground-muted mb-3 text-sm font-semibold uppercase tracking-wider">
          Available Flows
        </h3>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="border-card-border bg-card-bg h-16 animate-pulse rounded-lg border"
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {flows.map((flow) => (
              <div key={flow.id} className="border-card-border bg-card-bg rounded-lg border p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{flow.id}</p>
                    {flow.description && (
                      <p className="text-foreground-muted mt-0.5 text-sm">{flow.description}</p>
                    )}
                    <div className="mt-2 flex gap-1.5">
                      {flow.is_template && (
                        <span className="bg-interactive/10 text-interactive rounded-full px-2 py-0.5 text-xs font-medium">
                          Template
                        </span>
                      )}
                      {flow.has_schedule && (
                        <span className="bg-surface-hover text-foreground-muted flex items-center gap-1 rounded-full px-2 py-0.5 text-xs">
                          <Clock className="h-3 w-3" /> Scheduled
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedFlowId(flow.id);
                      setDialogOpen(true);
                    }}
                    className="bg-interactive text-foreground-inverse hover:bg-interactive-hover rounded-md px-3 py-1.5 text-sm font-medium"
                  >
                    <Play className="inline h-3.5 w-3.5" /> Trigger
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Executions */}
      {executions.length > 0 && (
        <section>
          <h3 className="text-foreground-muted mb-3 text-sm font-semibold uppercase tracking-wider">
            Executions
          </h3>
          <div className="space-y-2">
            {executions.map((exec) => {
              const isExpanded = expandedExecId === exec.execution_id;
              return (
                <div
                  key={exec.execution_id}
                  className="border-card-border bg-card-bg rounded-lg border"
                >
                  <button
                    onClick={() => setExpandedExecId(isExpanded ? null : exec.execution_id)}
                    className="flex w-full items-center justify-between p-4 text-left"
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_TEXT_COLORS[exec.status]}`}
                      >
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${STATUS_COLORS[exec.status]}`}
                        />
                        {exec.status}
                      </span>
                      <span className="text-sm font-medium">{exec.flow_id}</span>
                    </div>
                    <span className="text-foreground-muted text-sm">
                      {formatDuration(exec.started, exec.ended)}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="border-card-border border-t p-4">
                      {/* Task Runs */}
                      <div className="space-y-1.5">
                        {exec.task_runs.map((task) => {
                          const totalMs = exec.ended
                            ? new Date(exec.ended).getTime() - new Date(exec.started).getTime()
                            : Date.now() - new Date(exec.started).getTime();
                          const taskStart = task.started
                            ? new Date(task.started).getTime() - new Date(exec.started).getTime()
                            : 0;
                          const taskEnd = task.ended
                            ? new Date(task.ended).getTime() - new Date(exec.started).getTime()
                            : totalMs;
                          const leftPct = totalMs > 0 ? (taskStart / totalMs) * 100 : 0;
                          const widthPct =
                            totalMs > 0 ? ((taskEnd - taskStart) / totalMs) * 100 : 100;

                          return (
                            <div key={task.task_id} className="flex items-center gap-3">
                              <span className="w-28 truncate font-mono text-xs">
                                {task.task_id}
                              </span>
                              <div className="bg-surface-hover relative h-5 flex-1 rounded">
                                <div
                                  className={`absolute top-0 h-5 rounded ${STATUS_COLORS[task.status]} opacity-70`}
                                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                                />
                              </div>
                              <span
                                className={`w-16 text-right text-xs ${STATUS_TEXT_COLORS[task.status]}`}
                              >
                                {task.status}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Logs */}
                      {logs && logs.execution_id === exec.execution_id && (
                        <div className="mt-4">
                          <h4 className="text-foreground-muted mb-2 text-xs font-semibold uppercase tracking-wider">
                            Logs
                          </h4>
                          <div className="bg-surface-sunken max-h-64 overflow-y-auto rounded p-3 font-mono text-xs">
                            {logs.logs.map((log, i) => (
                              <div key={i} className="flex gap-2">
                                <span className="text-foreground-muted">
                                  {new Date(log.timestamp).toLocaleTimeString()}
                                </span>
                                <span
                                  className={
                                    log.level === "ERROR" ? "text-status-error" : "text-foreground"
                                  }
                                >
                                  [{log.level}]
                                </span>
                                <span>{log.message}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Trigger Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[32rem]">
          <DialogHeader>
            <DialogTitle>Trigger Workflow</DialogTitle>
            <DialogDescription>
              Configure and trigger the workflow: {selectedFlowId}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Flow</label>
              <select
                value={selectedFlowId}
                onChange={(e) => setSelectedFlowId(e.target.value)}
                className="border-input-border bg-input-bg w-full rounded-md border px-3 py-2 text-sm"
              >
                {flows.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Inputs (JSON)</label>
              <textarea
                value={inputsJson}
                onChange={(e) => {
                  setInputsJson(e.target.value);
                  setJsonError(null);
                }}
                rows={5}
                className="border-input-border bg-input-bg w-full rounded-md border px-3 py-2 font-mono text-sm"
              />
              {jsonError && (
                <p className="text-status-error mt-1 flex items-center gap-1 text-xs">
                  <AlertCircle className="h-3 w-3" /> {jsonError}
                </p>
              )}
            </div>
            <button
              onClick={handleTrigger}
              disabled={triggering || !selectedFlowId}
              className="bg-interactive text-foreground-inverse hover:bg-interactive-hover w-full rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              {triggering ? "Triggering…" : "Trigger"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
