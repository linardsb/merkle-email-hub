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

  const authHeaders = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${access_token}`,
  };

  // Ensure a client org exists — project creation requires client_org_id,
  // and the create-project dialog auto-selects the sole org when exactly one
  // is present, which keeps the dashboard "create a new project" smoke test
  // deterministic.
  const orgsListRes = await fetch(
    `${BACKEND_URL}/api/v1/orgs?page=1&page_size=1`,
    { headers: authHeaders }
  );
  if (!orgsListRes.ok) {
    throw new Error(
      `List client orgs failed: ${orgsListRes.status} ${await orgsListRes.text()}`
    );
  }
  const orgsList = await orgsListRes.json();
  let clientOrgId: number | null = orgsList.items?.[0]?.id ?? null;
  if (clientOrgId === null) {
    const orgCreateRes = await fetch(`${BACKEND_URL}/api/v1/orgs`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ name: "E2E Client", slug: "e2e-client" }),
    });
    if (!orgCreateRes.ok) {
      throw new Error(
        `Create client org failed: ${orgCreateRes.status} ${await orgCreateRes.text()}`
      );
    }
    clientOrgId = (await orgCreateRes.json()).id as number;
  }

  const projectRes = await fetch(`${BACKEND_URL}/api/v1/projects`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({
      name: `e2e-test-${Date.now()}`,
      description: "Automated E2E test project",
      client_org_id: clientOrgId,
    }),
  });
  if (!projectRes.ok) {
    throw new Error(
      `Create project failed: ${projectRes.status} ${await projectRes.text()}`
    );
  }
  const project = await projectRes.json();
  const projectId: number = project.id;

  const state = { access_token, projectId, clientOrgId };
  fs.writeFileSync(AUTH_STATE_PATH, JSON.stringify(state));
}

export default globalSetup;
