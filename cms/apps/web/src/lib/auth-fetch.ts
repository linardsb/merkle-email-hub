import type { Session } from "next-auth";

// Client-side token cache (60s TTL)
let cachedToken: string | null = null;
let cacheExpiry = 0;

const DEFAULT_TIMEOUT_MS = 30_000;
export const LONG_TIMEOUT_MS = 120_000;

/**
 * Fetch with automatic JWT authentication and request timeout.
 * Works in both server components and client components.
 * - Server: dynamically imports auth() from Auth.js
 * - Client: dynamically imports getSession() from next-auth/react
 */
export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number }
): Promise<Response> {
  const token = await getAccessToken();

  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const timeoutMs = init?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      headers,
      signal: init?.signal ?? controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    // Server context
    try {
      const { auth } = await import("../../auth");
      const session = await auth();
      return session?.accessToken ?? null;
    } catch {
      return null;
    }
  }

  // Client context with caching
  if (cachedToken && Date.now() < cacheExpiry) {
    return cachedToken;
  }

  try {
    const { getSession } = await import("next-auth/react");
    const session = (await getSession()) as (Session & { accessToken?: string }) | null;
    const token = session?.accessToken ?? null;

    if (token) {
      cachedToken = token;
      cacheExpiry = Date.now() + 60_000; // 60s cache
    }

    return token;
  } catch {
    return null;
  }
}

/**
 * Clear the client-side token cache.
 * Call after logout or when tokens are refreshed.
 */
export function clearTokenCache(): void {
  cachedToken = null;
  cacheExpiry = 0;
}
