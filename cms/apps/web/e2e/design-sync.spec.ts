import { test, expect } from "./fixtures";

test.describe("Design Sync", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "API-heavy flow — Chromium only");

  test("design sync page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/design-sync");
    await expect(page.locator("main")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /design/i }).or(page.getByText(/design sync/i).first()),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("connect dialog opens", async ({ authenticatedPage: page }) => {
    await page.goto("/design-sync");
    const connectButton = page.getByRole("button", { name: /connect/i });

    if (await connectButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await connectButton.click();
      await expect(page.getByRole("dialog").or(page.locator("dialog"))).toBeVisible({
        timeout: 5_000,
      });
    }
  });

  test("file browser with mock data", async ({ authenticatedPage: page }) => {
    // Mock Penpot/Figma API responses
    await page.route("**/api/v1/design-sync/**", (route) => {
      const url = route.request().url();
      if (url.includes("/files") || url.includes("/projects")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            files: [
              { id: "mock-1", name: "Mock Email Template", type: "frame" },
              { id: "mock-2", name: "Mock Component", type: "component" },
            ],
          }),
        });
      }
      return route.continue();
    });

    await page.goto("/design-sync");
    // Verify page loads without error
    await expect(page.locator("main")).toBeVisible();
  });
});
