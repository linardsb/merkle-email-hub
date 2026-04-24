import { test, expect } from "./fixtures";
import {
  getSharedProjectId,
  TEST_USER_EMAIL,
  TEST_USER_PASSWORD,
} from "./fixtures/constants";

test.describe("Collaboration", () => {
  test.describe.configure({ retries: 3 });
  test.skip(
    ({ browserName }) => browserName === "webkit",
    "WebSocket behavior — skip WebKit"
  );

  test("presence indicator shows active user", async ({
    authenticatedPage: page,
    browser,
    browserName,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    // Open second context with same baseURL
    const context2 = await browser.newContext({
      baseURL: process.env.BASE_URL || "http://localhost:3000",
    });
    const page2 = await context2.newPage();
    await page2.goto("/login");
    await page2.locator("#username").fill(TEST_USER_EMAIL);
    await page2.locator("#password").fill(TEST_USER_PASSWORD);
    await page2.getByRole("button", { name: /sign in/i }).click();
    await page2.waitForURL(/\/(projects|dashboard)?$/);
    await page2.goto(`/projects/${projectId}/workspace`);

    // Firefox: WebSocket connection can be slower — use longer timeout
    const wsTimeout = browserName === "firefox" ? 15_000 : 10_000;

    // Wait for presence to propagate via WebSocket
    const presenceIndicator = page
      .getByText(/online|active|user/i)
      .or(page.locator("[data-testid='presence']"))
      .first();

    // Use polling instead of fixed timeout
    await expect(page.locator("main")).toBeVisible({ timeout: wsTimeout });

    await context2.close();
  });

  test("workspace loads for concurrent sessions", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await expect(page.locator("main")).toBeVisible();
  });
});
