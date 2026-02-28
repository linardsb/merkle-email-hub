import { authFetch } from "./auth-fetch";
import { ApiError } from "./api-error";

/**
 * SWR fetcher that automatically injects JWT auth headers.
 * Parses backend error responses into typed ApiError instances.
 * Usage: useSWR("/api/v1/items", fetcher)
 */
export async function fetcher<T>(url: string): Promise<T> {
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
