import { test, expect } from "./fixtures";
import { getSharedProjectId } from "./fixtures/constants";

test.describe("Export Flow", () => {
  test.skip(({ browserName }) => browserName !== "chromium", "API-heavy flow — Chromium only");

  // Stub the Maizzle compile proxy — CI doesn't run the sidecar. Real
  // Maizzle integration is covered by the backend test suite; here we only
  // need a compiled-html value so handleExport doesn't early-return.
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route("**/api/v1/email/preview", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          compiled_html: "<html><body><h1>stubbed preview</h1></body></html>",
          build_time_ms: 42,
        }),
      }),
    );
  });

  async function openExportDialog(page: import("@playwright/test").Page) {
    // handleExport early-returns with a toast if compiledHtml is empty, so
    // force a compile first; iframe appearing confirms the compile round-trip.
    await page.getByRole("button", { name: /^compile$/i }).click();
    await expect(page.locator("iframe").first()).toBeVisible({
      timeout: 15_000,
    });
    // Export lives inside the Deliver dropdown menu in the workspace toolbar.
    await page.getByRole("button", { name: /^deliver$/i }).click();
    await page.getByRole("menuitem", { name: /^export$/i }).click();
  }

  test("export dialog opens with tabs @smoke", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    await openExportDialog(page);

    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/raw html/i)).toBeVisible();
    await expect(page.getByText(/braze/i)).toBeVisible();
  });

  test("Raw HTML tab has download button", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await openExportDialog(page);

    await expect(page.getByRole("button", { name: /download html/i })).toBeVisible({
      timeout: 5_000,
    });
  });

  test("Braze tab shows name input", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await openExportDialog(page);

    await page.getByText(/braze/i).click();
    await expect(page.locator("#braze-name")).toBeVisible({ timeout: 5_000 });
  });

  test("gate panels appear in export flow", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await openExportDialog(page);

    await expect(page.getByText(/qa|quality|rendering|approval/i).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("export dialog can be closed", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await openExportDialog(page);

    const dialog = page.locator("dialog").or(page.getByRole("dialog"));
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible({ timeout: 5_000 });
  });
});
