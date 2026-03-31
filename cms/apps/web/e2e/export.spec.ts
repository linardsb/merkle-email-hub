import { test, expect } from "./fixtures";
import { getSharedProjectId } from "./fixtures/constants";

test.describe("Export Flow", () => {
  test.skip(
    ({ browserName }) => browserName !== "chromium",
    "API-heavy flow — Chromium only"
  );

  test("export dialog opens with tabs @smoke", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);

    const exportButton = page.getByRole("button", { name: /export/i });
    await expect(exportButton).toBeVisible({ timeout: 10_000 });
    await exportButton.click();

    await expect(page.locator("dialog").or(page.getByRole("dialog"))).toBeVisible();
    await expect(page.getByText(/raw html/i)).toBeVisible();
    await expect(page.getByText(/braze/i)).toBeVisible();
  });

  test("Raw HTML tab has download button", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await page.getByRole("button", { name: /export/i }).click();

    await expect(
      page.getByRole("button", { name: /download html/i })
    ).toBeVisible({ timeout: 5_000 });
  });

  test("Braze tab shows name input", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await page.getByRole("button", { name: /export/i }).click();

    await page.getByText(/braze/i).click();
    await expect(page.locator("#braze-name")).toBeVisible({ timeout: 5_000 });
  });

  test("gate panels appear in export flow", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await page.getByRole("button", { name: /export/i }).click();

    await expect(
      page
        .getByText(/qa|quality|rendering|approval/i)
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("export dialog can be closed", async ({
    authenticatedPage: page,
  }) => {
    const projectId = getSharedProjectId();
    await page.goto(`/projects/${projectId}/workspace`);
    await page.getByRole("button", { name: /export/i }).click();

    const dialog = page.locator("dialog").or(page.getByRole("dialog"));
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible({ timeout: 5_000 });
  });
});
