"use client";

import { useCallback, useState } from "react";
import { authFetch, LONG_TIMEOUT_MS } from "@/lib/auth-fetch";
import type { BlueprintRunResponse } from "@email-hub/sdk";

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

interface UseBlueprintRunOptions {
  projectId: number;
}

interface BlueprintRunParams {
  blueprint_name: string;
  brief: string;
  initial_html?: string;
  persona_ids?: number[];
}

interface BlueprintResumeParams {
  run_id: string;
  blueprint_name: string;
  brief: string;
}

export function useBlueprintRun({ projectId }: UseBlueprintRunOptions) {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<BlueprintRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (params: BlueprintRunParams) => {
      setIsRunning(true);
      setError(null);
      setResult(null);

      try {
        if (IS_DEMO) {
          const { resolveDemo } = await import("@/lib/demo/resolver");
          await new Promise((r) => setTimeout(r, 2000 + Math.random() * 1000));
          const data = resolveDemo("/api/v1/blueprints/run") as BlueprintRunResponse;
          setResult(data);
          return data;
        }

        const res = await authFetch("/api/v1/blueprints/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...params,
            options: { project_id: projectId },
          }),
          timeoutMs: LONG_TIMEOUT_MS,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.error ?? "Blueprint run failed");
        }

        const data: BlueprintRunResponse = await res.json();
        setResult(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Blueprint run failed";
        setError(message);
        return null;
      } finally {
        setIsRunning(false);
      }
    },
    [projectId],
  );

  const resume = useCallback(
    async (params: BlueprintResumeParams) => {
      setIsRunning(true);
      setError(null);
      setResult(null);

      try {
        if (IS_DEMO) {
          const { resolveDemo } = await import("@/lib/demo/resolver");
          await new Promise((r) => setTimeout(r, 2000 + Math.random() * 1000));
          const data = resolveDemo("/api/v1/blueprints/resume") as BlueprintRunResponse;
          setResult(data);
          return data;
        }

        const res = await authFetch("/api/v1/blueprints/resume", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(params),
          timeoutMs: LONG_TIMEOUT_MS,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.error ?? "Resume failed");
        }

        const data: BlueprintRunResponse = await res.json();
        setResult(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Resume failed";
        setError(message);
        return null;
      } finally {
        setIsRunning(false);
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsRunning(false);
  }, []);

  return { run, resume, isRunning, result, error, reset };
}
