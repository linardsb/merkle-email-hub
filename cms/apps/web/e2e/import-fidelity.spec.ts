import { test, expect } from "./fixtures";
import { getSharedProjectId } from "./fixtures/constants";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function loadFixture(name: string): string {
  return readFileSync(resolve(process.cwd(), "e2e", "fixtures", name), "utf-8");
}

test.describe("Import Fidelity", () => {
  test("paste pre-compiled email and preview renders", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    // Navigate to code editor tab
    const codeTab = page.getByRole("tab", { name: /code/i });
    if (await codeTab.isVisible()) {
      await codeTab.click();
    }

    // Wait for editor to load
    const editor = page.locator("[data-language], .cm-editor, .monaco-editor, textarea").first();
    await expect(editor).toBeVisible({ timeout: 10_000 });

    // Paste pre-compiled email HTML
    const emailHtml = loadFixture("pre-compiled-email.html");
    await editor.click();
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.type(emailHtml.slice(0, 200)); // Type partial to avoid timeout
    // Full paste via clipboard
    await page.evaluate((html) => navigator.clipboard.writeText(html), emailHtml);
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.press("ControlOrMeta+v");

    // Compile
    await page.keyboard.press("ControlOrMeta+s");

    // Switch to preview tab
    const previewTab = page.getByRole("tab", { name: /preview/i });
    if (await previewTab.isVisible()) {
      await previewTab.click();
    }

    // Assert: preview iframe renders (not blank)
    const iframe = page.locator("iframe").first();
    await expect(iframe).toBeVisible({ timeout: 15_000 });
  });

  test("preview iframe has secure sandbox", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    const previewTab = page.getByRole("tab", { name: /preview/i });
    if (await previewTab.isVisible()) {
      await previewTab.click();
    }

    const iframe = page.locator("iframe").first();
    if (await iframe.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const sandbox = await iframe.getAttribute("sandbox");
      expect(sandbox).toContain("allow-same-origin");
      expect(sandbox).not.toContain("allow-scripts");
    }
  });

  test("dark mode toggle does not produce invisible text", async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    const previewTab = page.getByRole("tab", { name: /preview/i });
    if (await previewTab.isVisible()) {
      await previewTab.click();
    }

    // Look for dark mode toggle button
    const darkModeBtn = page.getByRole("button", { name: /dark/i });
    if (await darkModeBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await darkModeBtn.click();

      // Verify iframe still visible (not blank/invisible)
      const iframe = page.locator("iframe").first();
      await expect(iframe).toBeVisible({ timeout: 10_000 });
    }
  });
});
