import { test as base, expect } from "@playwright/test";
import { test } from "./fixtures";
import { TEST_USER_EMAIL, TEST_USER_PASSWORD } from "./fixtures/constants";

base.describe("Authentication", () => {
  base("login with valid credentials @smoke", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#username").fill(TEST_USER_EMAIL);
    await page.locator("#password").fill(TEST_USER_PASSWORD);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.waitForURL(/\/(projects|dashboard)?$/);
    await expect(page.locator("nav")).toBeVisible();
  });

  base("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#username").fill(TEST_USER_EMAIL);
    await page.locator("#password").fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  });

  test("logout redirects to login", async ({ authenticatedPage: page }) => {
    await expect(page.locator("nav")).toBeVisible();
    await page.getByRole("link", { name: /logout/i }).click();
    await page.waitForURL(/\/login/);
    await expect(page.locator("#username")).toBeVisible();
  });
});
