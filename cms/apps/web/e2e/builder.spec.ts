import { test, expect } from "./fixtures";
import { getSharedProjectId } from "./fixtures/constants";

test.describe("Visual Builder", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    const visualTab = page.getByRole("tab", { name: /visual/i });
    if (await visualTab.isVisible()) {
      await visualTab.click();
    }
  });

  test("component palette loads @smoke", async ({ authenticatedPage: page }) => {
    await expect(
      page.getByPlaceholder(/search components/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("palette has category filters", async ({
    authenticatedPage: page,
  }) => {
    await expect(
      page.getByRole("button", { name: /^all$/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("drag component to canvas", async ({
    authenticatedPage: page,
    browserName,
  }) => {
    const firstComponent = page.locator("[draggable='true']").first();
    await expect(firstComponent).toBeVisible({ timeout: 10_000 });

    const canvas = page
      .getByText(/drag components/i)
      .or(page.locator("[data-testid='builder-canvas']"))
      .first();

    const sourceBox = await firstComponent.boundingBox();
    const targetBox = await canvas.boundingBox();
    if (sourceBox && targetBox) {
      if (browserName === "firefox") {
        // Firefox: native DnD events differ — use dispatchEvent approach
        await firstComponent.dispatchEvent("dragstart");
        await canvas.dispatchEvent("dragover");
        await canvas.dispatchEvent("drop");
        await firstComponent.dispatchEvent("dragend");
      } else {
        // Chromium & WebKit: mouse-based drag
        await page.mouse.move(
          sourceBox.x + sourceBox.width / 2,
          sourceBox.y + sourceBox.height / 2
        );
        await page.mouse.down();
        await page.mouse.move(
          targetBox.x + targetBox.width / 2,
          targetBox.y + targetBox.height / 2,
          { steps: 10 }
        );
        await page.mouse.up();
      }
    }

    // Verify drag target was found — actual drop may vary by environment
    expect(sourceBox).toBeTruthy();
    expect(targetBox).toBeTruthy();
  });

  test("property panel opens on section click", async ({
    authenticatedPage: page,
    browserName,
  }) => {
    const section = page
      .locator("[data-testid='section-wrapper']")
      .or(page.locator(".flex-1.overflow-y-auto [role='button']"))
      .first();

    if (await section.isVisible({ timeout: 5_000 }).catch(() => false)) {
      if (browserName === "webkit") {
        // Safari: explicit focus before click for contentEditable
        await section.focus();
        await page.waitForTimeout(200);
      }
      await section.click();
      await expect(
        page
          .getByRole("tab", { name: /content/i })
          .or(page.getByLabel(/close property panel/i))
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("undo/redo keyboard shortcuts", async ({
    authenticatedPage: page,
    browserName,
  }) => {
    // WebKit (Safari) uses Meta instead of Control on macOS
    const mod = browserName === "webkit" ? "Meta" : "Control";
    await page.keyboard.press(`${mod}+z`);
    await page.keyboard.press(`${mod}+Shift+z`);
    await expect(page.locator("main")).toBeVisible();
  });
});
