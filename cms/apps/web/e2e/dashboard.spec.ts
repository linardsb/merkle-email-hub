import { test, expect } from "./fixtures";

test.describe("Dashboard & Projects", () => {
  test("dashboard loads with navigation @smoke", async ({ authenticatedPage: page }) => {
    await page.goto("/");
    await expect(page.locator("nav")).toBeVisible();
    await expect(page.getByRole("link", { name: /projects/i })).toBeVisible();
  });

  test("create a new project @smoke", async ({ authenticatedPage: page }) => {
    await page.goto("/projects");
    await page.getByRole("button", { name: /new project/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();

    const projectName = `E2E Project ${Date.now()}`;
    await page.locator("#project-name").fill(projectName);
    await page.locator("#project-description").fill("Created by E2E test");
    await page.getByRole("button", { name: /create project/i }).click();

    await expect(page.getByRole("dialog")).not.toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(projectName)).toBeVisible();
  });

  test("search filters projects", async ({ authenticatedPage: page }) => {
    await page.goto("/projects");
    const searchInput = page.getByPlaceholder(/search/i);
    await searchInput.fill("e2e-test-");
    await expect(page.getByText(/e2e-test-/i).first()).toBeVisible({ timeout: 5_000 });
  });
});
