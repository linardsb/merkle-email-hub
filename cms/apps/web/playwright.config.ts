import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

const browser = process.env.BROWSER || "chromium";

/** Build project list from BROWSER env var (chromium | firefox | webkit | all) */
function getProjects(): NonNullable<PlaywrightTestConfig["projects"]> {
  const chromium = {
    name: "chromium" as const,
    use: { ...devices["Desktop Chrome"] },
  };
  const firefox = {
    name: "firefox" as const,
    use: { ...devices["Desktop Firefox"] },
  };
  const webkit = {
    name: "webkit" as const,
    use: { ...devices["Desktop Safari"] },
  };

  const all = [chromium, firefox, webkit];
  if (browser === "all") return all;
  if (browser === "firefox") return [firefox];
  if (browser === "webkit") return [webkit];
  return [chromium];
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }]],
  timeout: 30_000,
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: getProjects(),
  webServer: {
    command: "pnpm dev",
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
