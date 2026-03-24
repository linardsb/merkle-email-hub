import { test as base, type Page } from "@playwright/test";
import {
  BACKEND_URL,
  TEST_USER_EMAIL,
  TEST_USER_PASSWORD,
} from "./constants";

type AuthFixtures = {
  authenticatedPage: Page;
  apiToken: string;
};

export const test = base.extend<AuthFixtures>({
  apiToken: async ({}, use) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: TEST_USER_EMAIL,
        password: TEST_USER_PASSWORD,
      }),
    });
    if (!res.ok) {
      throw new Error(`Login failed in apiToken fixture: ${res.status}`);
    }
    const data = await res.json();
    if (!data.access_token) {
      throw new Error("Login response missing access_token");
    }
    await use(data.access_token);
  },

  authenticatedPage: async ({ page }, use) => {
    await page.goto("/login");
    await page.locator("#username").fill(TEST_USER_EMAIL);
    await page.locator("#password").fill(TEST_USER_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/^\/$|\/projects|\/dashboard/);
    await use(page);
  },
});
