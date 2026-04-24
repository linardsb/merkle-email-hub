import fs from "node:fs";
import path from "node:path";
import { BACKEND_URL } from "./fixtures/constants";

const AUTH_STATE_PATH = path.resolve(process.cwd(), "e2e", ".e2e-auth-state");

async function globalTeardown() {
  if (!fs.existsSync(AUTH_STATE_PATH)) return;

  try {
    const state = JSON.parse(fs.readFileSync(AUTH_STATE_PATH, "utf-8"));

    if (state.projectId && state.access_token) {
      await fetch(`${BACKEND_URL}/api/v1/projects/${state.projectId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${state.access_token}` },
      }).catch(() => {});
    }
  } finally {
    fs.unlinkSync(AUTH_STATE_PATH);
  }
}

export default globalTeardown;
