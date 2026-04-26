import { NextRequest } from "next/server";
import { auth } from "../../../../../auth";

const BACKEND_URL = (() => {
  const url = process.env.BACKEND_URL;
  if (url) return url;
  if (process.env.NODE_ENV === "production") {
    throw new Error("BACKEND_URL is required in production");
  }
  return "http://localhost:8891";
})();

/**
 * Proxy all /api/v1/* requests to the FastAPI backend.
 * Injects the JWT access token from the NextAuth session.
 */
async function proxy(req: NextRequest) {
  const url = new URL(req.url);
  const target = `${BACKEND_URL}${url.pathname}${url.search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("cookie"); // Don't forward session cookies to backend

  // Forward client IP so backend rate limiter can distinguish users
  if (!headers.has("X-Real-IP")) {
    const forwarded = req.headers.get("x-forwarded-for");
    const clientIp =
      forwarded?.split(",")[0]?.trim() ?? req.headers.get("x-real-ip") ?? "127.0.0.1";
    headers.set("X-Real-IP", clientIp);
  }

  // Always overwrite Authorization with the session token when a session exists.
  // Never trust a client-supplied Authorization header on this proxy.
  try {
    const session = await auth();
    if (session?.accessToken) {
      headers.set("Authorization", `Bearer ${session.accessToken}`);
    } else {
      headers.delete("Authorization");
    }
  } catch {
    headers.delete("Authorization");
  }

  const res = await fetch(target, {
    method: req.method,
    headers,
    body: req.body,
    // @ts-expect-error -- duplex required for streaming body in Node 18+
    duplex: "half",
  });

  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: res.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
