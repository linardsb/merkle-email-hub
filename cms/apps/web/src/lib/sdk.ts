import { client } from "@email-hub/sdk";
import { authFetch } from "./auth-fetch";

// Configure the SDK client
client.setConfig({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "/api/proxy",
});

// Auth interceptor — server-side token injection
client.interceptors.request.use(async (request) => {
  if (typeof window === "undefined") {
    try {
      const { auth } = await import("@/auth");
      const session = await auth();
      if (session?.accessToken) {
        request.headers.set("Authorization", `Bearer ${session.accessToken}`);
      }
    } catch {
      // Auth not available
    }
  }
  return request;
});

// 401 response interceptor — redirect to login on expired session (client-side only)
client.interceptors.response.use(async (response) => {
  if (response.status === 401 && typeof window !== "undefined") {
    const { signOut } = await import("next-auth/react");
    await signOut({ callbackUrl: "/login" });
  }
  return response;
});

// 429 rate limit retry interceptor — retry once with Retry-After backoff
client.interceptors.response.use(async (response, request) => {
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    const delayMs = retryAfter ? parseInt(retryAfter, 10) * 1000 : 2000;
    const retryCount = (request as Request & { __retryCount?: number }).__retryCount ?? 0;

    if (retryCount < 1) {
      await new Promise((resolve) => setTimeout(resolve, Math.min(delayMs, 10_000)));
      (request as Request & { __retryCount?: number }).__retryCount = retryCount + 1;
      return fetch(request);
    }
  }
  return response;
});

export { client };
export { authFetch };
