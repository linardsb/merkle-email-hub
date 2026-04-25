import { test, expect } from "./fixtures";

test.describe("Ecosystem Dashboard", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "API-heavy flow — Chromium only");

  test("ecosystem page loads with stat cards", async ({ authenticatedPage: page }) => {
    await page.goto("/ecosystem");
    await expect(page.locator("main")).toBeVisible();

    // Stat cards: Plugins, Workflows, Reports, Penpot
    await expect(page.getByText(/plugins/i).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/workflows/i).first()).toBeVisible();
    await expect(page.getByText(/reports/i).first()).toBeVisible();
    await expect(page.getByText(/penpot/i).first()).toBeVisible();
  });

  test("quadrant cards with view-all links", async ({ authenticatedPage: page }) => {
    await page.goto("/ecosystem");
    await expect(page.locator("main")).toBeVisible();

    // Look for "View All" links in quadrant cards
    const viewAllLinks = page.getByText(/view all/i);
    await expect(viewAllLinks.first()).toBeVisible({ timeout: 10_000 });
  });
});
