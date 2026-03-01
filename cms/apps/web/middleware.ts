


import { auth } from "@/auth";
import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import type { AppRole } from "@/auth";

const intlMiddleware = createMiddleware({
  locales: ["en"],
  defaultLocale: "en",
});

// Route permission map — configure which roles can access each route
const ROLE_PERMISSIONS: Record<string, AppRole[]> = {
  "/dashboard": ["admin", "developer", "viewer"],
  "/projects": ["admin", "developer", "viewer"],
  "/example": ["admin", "developer", "viewer"],
  "/components": ["admin", "developer", "viewer"],
  "/users": ["admin"],
  "/approvals": ["admin", "developer", "viewer"],
  "/connectors": ["admin", "developer", "viewer"],
  "/intelligence": ["admin", "developer", "viewer"],
  "/knowledge": ["admin", "developer", "viewer"],
};

const PUBLIC_ROUTES = ["/login"];

function getRouteKey(pathname: string): string | null {
  // Strip locale prefix: /en/dashboard → /dashboard
  const withoutLocale = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "") || "/";

  for (const route of Object.keys(ROLE_PERMISSIONS)) {
    if (withoutLocale === route || withoutLocale.startsWith(route + "/")) {
      return route;
    }
  }
  return null;
}

function isPublicRoute(pathname: string): boolean {
  const withoutLocale = pathname.replace(/^\/[a-z]{2}(?=\/|$)/, "") || "/";
  return PUBLIC_ROUTES.some(
    (r) => withoutLocale === r || withoutLocale.startsWith(r + "/")
  );
}

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip static assets and API routes
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Apply i18n middleware
  const intlResponse = intlMiddleware(request);

  // Public routes don't need auth
  if (isPublicRoute(pathname)) {
    return intlResponse;
  }

  // Demo mode: skip auth checks entirely
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return intlResponse;
  }

  // Check authentication — wrapped in try/catch because next-auth beta
  // can throw if session resolution fails, which kills the entire middleware
  try {
    const session = await auth();

    if (!session?.user) {
      const locale = pathname.match(/^\/([a-z]{2})/)?.[1] || "en";
      const loginUrl = new URL(`/${locale}/login`, request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Check RBAC
    const routeKey = getRouteKey(pathname);
    if (routeKey) {
      const allowedRoles = ROLE_PERMISSIONS[routeKey];
      const userRole: string = session.user.role || "viewer";
      if (allowedRoles && !allowedRoles.includes(userRole as AppRole)) {
        const locale = pathname.match(/^\/([a-z]{2})/)?.[1] || "en";
        return NextResponse.redirect(
          new URL(`/${locale}/unauthorized`, request.url)
        );
      }
    }
  } catch {
    // Auth failed — let the page render (login page handles its own redirect)
  }

  return intlResponse;
}

export const config = {
  matcher: ["/((?!_next|api|.*\\..*).*)"],
};
