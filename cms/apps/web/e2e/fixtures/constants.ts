import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const BACKEND_URL =
  process.env.BACKEND_URL || "http://localhost:8891";
export const TEST_USER_EMAIL = "admin@email-hub.dev";
export const TEST_USER_PASSWORD = "admin";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_STATE_PATH = path.join(__dirname, "..", ".e2e-auth-state");

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
    throw new Error(
      "Shared test project was not created in global-setup. Check backend logs."
    );
  }
  return state.projectId;
}
