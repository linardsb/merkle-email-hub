
import { auth } from "@/auth";
import { NextRequest, NextResponse } from "next/server";
import type { AppRole } from "@/auth";

// Route permission map — configure which roles can access each route
const ROLE_PERMISSIONS: Record<string, AppRole[]> = {
  "/": ["admin", "developer", "viewer"],
  "/projects": ["admin", "developer", "viewer"],
  "/example": ["admin", "developer", "viewer"],
  "/components": ["admin", "developer", "viewer"],
  "/users": ["admin"],
  "/approvals": ["admin", "developer", "viewer"],
  "/connectors": ["admin", "developer", "viewer"],
  "/intelligence": ["admin", "developer", "viewer"],
  "/knowledge": ["admin", "developer", "viewer"],
  "/figma": ["admin", "developer", "viewer"],
};

const PUBLIC_ROUTES = ["/login"];

function getRouteKey(pathname: string): string | null {
  for (const route of Object.keys(ROLE_PERMISSIONS)) {
    if (pathname === route || pathname.startsWith(route + "/")) {
      return route;
    }
  }
  return null;
}

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (r) => pathname === r || pathname.startsWith(r + "/")
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

  // Public routes don't need auth
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // Check authentication — wrapped in try/catch because next-auth beta
  // can throw if session resolution fails, which kills the entire middleware
  try {
    const session = await auth();

    if (!session?.user) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Check RBAC
    const routeKey = getRouteKey(pathname);
    if (routeKey) {
      const allowedRoles = ROLE_PERMISSIONS[routeKey];
      const userRole: string = session.user.role || "viewer";
      if (allowedRoles && !allowedRoles.includes(userRole as AppRole)) {
        return NextResponse.redirect(
          new URL("/unauthorized", request.url)
        );
      }
    }
  } catch {
    // Auth failed — let the page render (login page handles its own redirect)
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|api|.*\\..*).*)"],
};
