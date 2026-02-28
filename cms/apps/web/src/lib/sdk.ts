import { client } from "@merkle-email-hub/sdk";
import { authFetch } from "./auth-fetch";

// Configure the SDK client
client.setConfig({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "/api/proxy",
});

// Add auth interceptor
client.interceptors.request.use(async (request) => {
  if (typeof window === "undefined") {
    // Server-side: inject token directly
    try {
      const { auth } = await import("@/auth");
      const session = await auth();
      if ((session as any)?.accessToken) {
        request.headers.set(
          "Authorization",
          `Bearer ${(session as any).accessToken}`
        );
      }
    } catch {
      // Auth not available
    }
  }
  return request;
});

export { client };
export { authFetch };
