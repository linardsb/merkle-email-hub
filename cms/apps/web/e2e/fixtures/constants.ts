import fs from "node:fs";
import path from "node:path";

export const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8891";
export const TEST_USER_EMAIL = "admin@email-hub.dev";
export const TEST_USER_PASSWORD = "admin";

// Playwright runs from the package root (cms/apps/web); resolving from cwd
// avoids __dirname/import.meta.url which swing between CJS and ESM loader modes.
const AUTH_STATE_PATH = path.resolve(process.cwd(), "e2e", ".e2e-auth-state");

interface AuthState {
  access_token: string;
  projectId: number | null;
}

export function readAuthState(): AuthState {
  const raw = fs.readFileSync(AUTH_STATE_PATH, "utf-8");
  return JSON.parse(raw) as AuthState;
}

export function getSharedProjectId(): number {
  const state = readAuthState();
  if (state.projectId == null) {
    throw new Error("Shared test project was not created in global-setup. Check backend logs.");
  }
  return state.projectId;
}
