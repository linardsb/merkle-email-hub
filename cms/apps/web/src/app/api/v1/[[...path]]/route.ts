import { NextRequest } from "next/server";
import { auth } from "../../../../../auth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8891";

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

  // If no Authorization header present, inject JWT from NextAuth session
  if (!headers.has("Authorization")) {
    try {
      const session = await auth();
      if (session?.accessToken) {
        headers.set("Authorization", `Bearer ${session.accessToken}`);
      }
    } catch {
      // Auth unavailable — forward without token
    }
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
