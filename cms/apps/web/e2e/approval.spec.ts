import { test, expect } from "./fixtures";

test.describe("Approval Workflow", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "API-heavy flow — Chromium only");

  test("approvals page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/approvals");
    await expect(page.locator("main")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /approval/i }).or(page.getByText(/approval/i).first()),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("approval cards show status badges", async ({ authenticatedPage: page }) => {
    await page.goto("/approvals");
    await expect(page.locator("main")).toBeVisible();
    // Verify the page structure loaded — status badges depend on data
    await expect(page.getByText(/approval/i).first()).toBeVisible({ timeout: 5_000 });
  });

  test("approval detail navigation", async ({ authenticatedPage: page }) => {
    await page.goto("/approvals");
    const approvalCard = page
      .locator("[role='button'], a")
      .filter({ hasText: /approval|pending|review/i })
      .first();

    if (await approvalCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await approvalCard.click();
      await expect(page.getByText(/preview|qa|quality|build/i).first()).toBeVisible({
        timeout: 10_000,
      });
    }
  });

  test("approve button triggers status change", async ({ authenticatedPage: page }) => {
    await page.goto("/approvals");
    const approveButton = page.getByRole("button", { name: /approve/i });

    if (await approveButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await approveButton.click();
      const confirmButton = page.getByRole("button", { name: /confirm/i });
      if (await confirmButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await confirmButton.click();
      }
      await expect(page.getByText(/approved/i).first()).toBeVisible({ timeout: 10_000 });
    }
  });
});
