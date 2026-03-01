import { authFetch } from "./auth-fetch";
import { ApiError } from "./api-error";

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

/**
 * SWR fetcher that automatically injects JWT auth headers.
 * In demo mode, returns mock data from the resolver instead.
 * Usage: useSWR("/api/v1/items", fetcher)
 */
export async function fetcher<T>(url: string): Promise<T> {
  if (IS_DEMO) {
    const { resolveDemo } = await import("./demo/resolver");
    const data = resolveDemo(url);
    if (data !== null) {
      // Simulate realistic network delay
      await new Promise((r) => setTimeout(r, 200 + Math.random() * 200));
      return data as T;
    }
  }

  const res = await authFetch(url);

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
