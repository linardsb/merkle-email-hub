import { authFetch, LONG_TIMEOUT_MS } from "./auth-fetch";
import { ApiError } from "./api-error";

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

async function tryDemoMutation<T>(url: string, arg: unknown): Promise<T | null> {
  if (!IS_DEMO) return null;
  const { resolveDemoMutation } = await import("./demo/mutation-resolver");
  const data = resolveDemoMutation(url, arg);
  if (data !== null) {
    await new Promise((r) => setTimeout(r, 300 + Math.random() * 400));
    return data as T;
  }
  return null;
}

/**
 * Generic POST mutation fetcher for useSWRMutation.
 * Usage: useSWRMutation("/api/v1/foo", mutationFetcher)
 */
export async function mutationFetcher<T>(
  url: string,
  { arg }: { arg: unknown }
): Promise<T> {
  const demo = await tryDemoMutation<T>(url, arg);
  if (demo !== null) return demo;

  const res = await authFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
  });

  if (!res.ok) {
    let message = "Request failed";
    let code: string | undefined;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
      if (body.type) code = body.type;
    } catch {
      message = res.statusText || message;
    }
    throw new ApiError(res.status, message, code);
  }

  return res.json();
}

/**
 * POST mutation fetcher with 120s timeout for long-running operations
 * (email builds, AI generation, QA runs).
 */
export async function longMutationFetcher<T>(
  url: string,
  { arg }: { arg: unknown }
): Promise<T> {
  const demo = await tryDemoMutation<T>(url, arg);
  if (demo !== null) return demo;

  const res = await authFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arg),
    timeoutMs: LONG_TIMEOUT_MS,
  });

  if (!res.ok) {
    let message = "Request failed";
    let code: string | undefined;
    try {
      const body = await res.json();
      if (body.error) message = body.error;
      if (body.type) code = body.type;
    } catch {
      message = res.statusText || message;
    }
    throw new ApiError(res.status, message, code);
  }

  return res.json();
}
