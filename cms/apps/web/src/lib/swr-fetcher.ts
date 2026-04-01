import { authFetch } from "./auth-fetch";
import { ApiError } from "./api-error";

/**
 * SWR fetcher that automatically injects JWT auth headers.
 * Usage: useSWR("/api/v1/items", fetcher)
 *
 * ## 304 Not Modified handling
 *
 * When the backend sends ETag headers, browsers handle 304 responses
 * transparently via the HTTP cache — the fetcher never sees them.
 * In SSR (Node.js fetch), 304 surfaces with an empty body. Returning
 * undefined tells SWR to keep its cached data, which is the correct
 * semantic for "data unchanged".
 */
export async function fetcher<T>(url: string): Promise<T> {
  const res = await authFetch(url);

  // 304 Not Modified — data unchanged. In SSR, this surfaces as an
  // empty-body response. Return undefined so SWR keeps cached data.
  if (res.status === 304) {
    return undefined as unknown as T;
  }

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
