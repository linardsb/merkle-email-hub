import { test as base } from "@playwright/test";
import {
  BACKEND_URL,
  TEST_USER_EMAIL,
  TEST_USER_PASSWORD,
} from "./constants";

export class ApiHelper {
  constructor(private token: string) {}

  private headers() {
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${this.token}`,
    };
  }

  async createProject(name: string) {
    const orgsRes = await fetch(
      `${BACKEND_URL}/api/v1/projects/orgs?page=1&page_size=1`,
      { headers: this.headers() }
    );
    if (!orgsRes.ok) {
      throw new Error(`list orgs failed: ${orgsRes.status}`);
    }
    const orgs = await orgsRes.json();
    const clientOrgId = orgs.items?.[0]?.id;
    if (!clientOrgId) {
      throw new Error(
        "No client org available; global-setup should have created one"
      );
    }
    const res = await fetch(`${BACKEND_URL}/api/v1/projects`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        name,
        description: "E2E test project",
        client_org_id: clientOrgId,
      }),
    });
    if (!res.ok) {
      throw new Error(`createProject failed: ${res.status} ${await res.text()}`);
    }
    return res.json();
  }

  async deleteProject(id: number) {
    await fetch(`${BACKEND_URL}/api/v1/projects/${id}`, {
      method: "DELETE",
      headers: this.headers(),
    }).catch(() => {});
  }

  async createApproval(projectId: number, buildId: number) {
    const res = await fetch(`${BACKEND_URL}/api/v1/approvals`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        project_id: projectId,
        build_id: buildId,
        note: "E2E test approval request",
      }),
    });
    if (!res.ok) {
      throw new Error(`createApproval failed: ${res.status}`);
    }
    return res.json();
  }

  async decideApproval(approvalId: number, decision: string) {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/approvals/${approvalId}/decide`,
      {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ decision, note: "E2E test decision" }),
      }
    );
    if (!res.ok) {
      throw new Error(`decideApproval failed: ${res.status}`);
    }
    return res.json();
  }
}

type ApiFixtures = {
  api: ApiHelper;
};

export const test = base.extend<ApiFixtures>({
  api: async ({}, use) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: TEST_USER_EMAIL,
        password: TEST_USER_PASSWORD,
      }),
    });
    if (!res.ok) {
      throw new Error(`Login failed in api fixture: ${res.status}`);
    }
    const data = await res.json();
    if (!data.access_token) {
      throw new Error("Login response missing access_token");
    }
    await use(new ApiHelper(data.access_token));
  },
});
