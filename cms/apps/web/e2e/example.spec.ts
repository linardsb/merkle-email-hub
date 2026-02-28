import { test, expect } from "@playwright/test";

test.describe("Example Items Page", () => {
  test("should display page title", async ({ page }) => {
    await page.goto("/dashboard");
    // Navigate to example page
    await page.getByRole("link", { name: /items/i }).click();
    await expect(page.getByRole("heading", { name: /items/i })).toBeVisible();
  });

  test("should show search input", async ({ page }) => {
    await page.goto("/example");
    await expect(
      page.getByPlaceholder(/search/i)
    ).toBeVisible();
  });

  test("should show create button", async ({ page }) => {
    await page.goto("/example");
    await expect(
      page.getByRole("button", { name: /create/i })
    ).toBeVisible();
  });
});
