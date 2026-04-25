import { test, expect } from "./fixtures";
import { getSharedProjectId } from "./fixtures/constants";

test.describe("Workspace", () => {
  test("workspace page loads @smoke", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await expect(page.getByRole("banner")).toBeVisible({ timeout: 15_000 });
  });

  test("code editor loads with content @smoke", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    const codeTab = page.getByRole("tab", { name: /code/i });
    if (await codeTab.isVisible()) {
      await codeTab.click();
    }
    await expect(
      page.locator("[data-language], .cm-editor, .monaco-editor, textarea").first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("visual builder tab loads", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    const visualTab = page.getByRole("tab", { name: /visual/i });
    if (await visualTab.isVisible()) {
      await visualTab.click();
    }
    await expect(
      page
        .getByText(/drag components/i)
        .or(page.locator("[data-testid='builder-canvas']"))
        .or(page.locator(".flex-1.overflow-y-auto").first()),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("preview tab renders iframe @smoke", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    // Stub the Maizzle compile proxy — CI doesn't run the sidecar. The UI
    // contract we care about here is: compile → compiledHtml set → iframe
    // mounts. Real Maizzle integration is covered by the backend test suite.
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
    await page.goto(`/projects/${projectId}/workspace`);
    await page.getByRole("button", { name: /^compile$/i }).click();
    await expect(page.locator("iframe").first()).toBeVisible({ timeout: 15_000 });
  });

  test("QA panel shows check results", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    const qaButton = page.getByRole("button", { name: /qa|quality/i });
    if (await qaButton.isVisible()) {
      await qaButton.click();
    }
    await expect(page.getByText(/pass|fail|warning|check/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});
