import { authFetch } from "./auth-fetch";

/**
 * SWR fetcher that automatically injects JWT auth headers.
 * Usage: useSWR("/api/v1/items", fetcher)
 */
export async function fetcher<T>(url: string): Promise<T> {
  const res = await authFetch(url);

  if (!res.ok) {
    const error = new Error("Fetch failed") as Error & { status: number };
    error.status = res.status;
    throw error;
  }

  return res.json();
}
