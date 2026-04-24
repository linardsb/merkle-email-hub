import fs from "node:fs";
import path from "node:path";
import {
  BACKEND_URL,
  TEST_USER_EMAIL,
  TEST_USER_PASSWORD,
} from "./fixtures/constants";

const AUTH_STATE_PATH = path.resolve(process.cwd(), "e2e", ".e2e-auth-state");

async function waitForHealth(url: string, retries = 10, intervalMs = 2000) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`${url}/health`);
      if (res.ok) return;
    } catch {
      // server not ready yet
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Backend not healthy after ${retries} retries`);
}

async function globalSetup() {
  await waitForHealth(BACKEND_URL);

  await fetch(`${BACKEND_URL}/api/v1/auth/bootstrap`, { method: "POST" });

  const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: TEST_USER_EMAIL,
      password: TEST_USER_PASSWORD,
    }),
  });
  if (!loginRes.ok) {
    throw new Error(`Login failed: ${loginRes.status}`);
  }
  const loginData = await loginRes.json();
  const access_token = loginData.access_token;
  if (!access_token || typeof access_token !== "string") {
    throw new Error(
      `Login response missing access_token: ${JSON.stringify(loginData)}`
    );
  }

  const projectRes = await fetch(`${BACKEND_URL}/api/v1/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access_token}`,
    },
    body: JSON.stringify({
      name: `e2e-test-${Date.now()}`,
      description: "Automated E2E test project",
      category: "promotional",
      target_esp: "raw_html",
    }),
  });

  let projectId: number | null = null;
  if (projectRes.ok) {
    const project = await projectRes.json();
    projectId = project.id;
  }

  const state = { access_token, projectId };
  fs.writeFileSync(AUTH_STATE_PATH, JSON.stringify(state));
}

export default globalSetup;
