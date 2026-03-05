import type {
  ScreenshotResult,
  RenderingTest,
  RenderingDiff,
  RenderingComparisonResponse,
} from "@/types/rendering";

// ── Seeded hash (same as qa-results.ts) ──
function seededHash(seed: number): number {
  return ((seed * 2654435761) >>> 0) / 4294967296;
}

// ── Client definitions (used only for demo data generation) ──
interface DemoClient {
  id: string;
  name: string;
  category: string;
  os: string;
}

const DEMO_CLIENTS: DemoClient[] = [
  // Desktop (7)
  { id: "outlook_2016", name: "Outlook 2016", category: "desktop", os: "windows" },
  { id: "outlook_2019", name: "Outlook 2019", category: "desktop", os: "windows" },
  { id: "outlook_365", name: "Outlook 365", category: "desktop", os: "windows" },
  { id: "outlook_mac", name: "Outlook Mac", category: "desktop", os: "macos" },
  { id: "apple_mail_macos", name: "Apple Mail macOS", category: "desktop", os: "macos" },
  { id: "thunderbird", name: "Thunderbird", category: "desktop", os: "linux" },
  { id: "windows_mail", name: "Windows Mail", category: "desktop", os: "windows" },
  // Webmail (8)
  { id: "gmail_web", name: "Gmail", category: "web", os: "web" },
  { id: "yahoo_web", name: "Yahoo Mail", category: "web", os: "web" },
  { id: "outlook_com", name: "Outlook.com", category: "web", os: "web" },
  { id: "aol_web", name: "AOL Mail", category: "web", os: "web" },
  { id: "protonmail", name: "ProtonMail", category: "web", os: "web" },
  { id: "fastmail", name: "Fastmail", category: "web", os: "web" },
  { id: "gmail_workspace", name: "Gmail Workspace", category: "web", os: "web" },
  { id: "zoho_mail", name: "Zoho Mail", category: "web", os: "web" },
  // Mobile (10)
  { id: "iphone_16", name: "iPhone 16 Mail", category: "mobile", os: "ios" },
  { id: "iphone_15", name: "iPhone 15 Mail", category: "mobile", os: "ios" },
  { id: "ipad_mail", name: "iPad Mail", category: "mobile", os: "ios" },
  { id: "gmail_android", name: "Gmail Android", category: "mobile", os: "android" },
  { id: "gmail_ios", name: "Gmail iOS", category: "mobile", os: "ios" },
  { id: "samsung_mail", name: "Samsung Mail", category: "mobile", os: "android" },
  { id: "outlook_ios", name: "Outlook iOS", category: "mobile", os: "ios" },
  { id: "outlook_android", name: "Outlook Android", category: "mobile", os: "android" },
  { id: "yahoo_mobile", name: "Yahoo Mobile", category: "mobile", os: "android" },
  { id: "ios_dark_mode", name: "iOS Dark Mode", category: "dark_mode", os: "ios" },
];

// ── Inline SVG email mockup generator ──
function hslColor(h: number, s: number, l: number): string {
  return `hsl(${Math.round(h)},${Math.round(s)}%,${Math.round(l)}%)`;
}

function generateEmailMockupSvg(clientId: string, testId: number, status: string): string {
  const seed = clientId.length * 17 + testId * 31;
  const hue = (seededHash(seed) * 360) % 360;
  const isDark = clientId === "ios_dark_mode";
  const isOutlookDesktop = clientId.startsWith("outlook_2") || clientId === "outlook_365" || clientId === "windows_mail";
  const isGmail = clientId.startsWith("gmail") || clientId === "gmail_workspace";
  const isMobile = clientId.startsWith("iphone") || clientId === "ipad_mail" || clientId.includes("android") || clientId === "yahoo_mobile" || clientId === "samsung_mail";

  const pageBg = isDark ? "#121218" : "#f0f0f0";
  const cardBg = isDark ? "#1e1e2a" : "#ffffff";
  const headerBg = hslColor(hue, 65, isDark ? 35 : 45);
  const heroBg = hslColor(hue, 50, isDark ? 25 : 85);
  const textColor = isDark ? "#888899" : "#cccccc";
  const ctaBg = hslColor(hue, 70, isDark ? 45 : 50);
  const footerColor = isDark ? "#555566" : "#dddddd";

  const cardW = isMobile ? 480 : 520;
  const cardX = (600 - cardW) / 2;
  const heroShift = isOutlookDesktop ? 8 : 0;
  const heroGap = isOutlookDesktop ? 12 : 0;
  const clipLine = isGmail;

  const statusDot = status === "complete" ? "#22c55e" : status === "failed" ? "#ef4444" : "#a3a3a3";

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <rect width="600" height="400" fill="${pageBg}"/>
  <rect x="${cardX}" y="16" width="${cardW}" height="368" rx="4" fill="${cardBg}" stroke="${isDark ? "#2a2a3a" : "#e5e5e5"}" stroke-width="1"/>
  <rect x="${cardX}" y="16" width="${cardW}" height="44" rx="4" fill="${headerBg}"/>
  <rect x="${cardX + 16}" y="30" width="80" height="16" rx="2" fill="${isDark ? "#ffffff33" : "#ffffff88"}"/>
  <rect x="${cardX + cardW - 96}" y="33" width="60" height="10" rx="2" fill="${isDark ? "#ffffff22" : "#ffffff55"}"/>
  <rect x="${cardX + 20 + heroShift}" y="${68 + heroGap}" width="${cardW - 40}" height="120" rx="3" fill="${heroBg}"/>
  <rect x="${cardX + (cardW / 2) - 60}" y="${108 + heroGap}" width="120" height="14" rx="2" fill="${isDark ? "#ffffff18" : "#00000012"}"/>
  <rect x="${cardX + (cardW / 2) - 40}" y="${128 + heroGap}" width="80" height="10" rx="2" fill="${isDark ? "#ffffff10" : "#00000008"}"/>
  <rect x="${cardX + 24}" y="${200 + heroGap}" width="${cardW - 48}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${216 + heroGap}" width="${cardW - 80}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${232 + heroGap}" width="${cardW - 60}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${248 + heroGap}" width="${cardW - 100}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + (cardW / 2) - 60}" y="${270 + heroGap}" width="120" height="32" rx="4" fill="${ctaBg}"/>
  <rect x="${cardX + (cardW / 2) - 30}" y="${282 + heroGap}" width="60" height="8" rx="2" fill="#ffffffcc"/>
  <rect x="${cardX + 24}" y="${318 + heroGap}" width="${cardW - 48}" height="1" fill="${footerColor}"/>
  <rect x="${cardX + (cardW / 2) - 70}" y="${328 + heroGap}" width="140" height="6" rx="1" fill="${footerColor}"/>
  <rect x="${cardX + (cardW / 2) - 50}" y="${340 + heroGap}" width="100" height="6" rx="1" fill="${footerColor}"/>
  ${clipLine ? `<line x1="${cardX + 10}" y1="350" x2="${cardX + cardW - 10}" y2="350" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>
  <text x="${cardX + cardW - 16}" y="348" font-size="8" fill="#ef4444" text-anchor="end" opacity="0.6" font-family="sans-serif">clipped</text>` : ""}
  <circle cx="${cardX + cardW - 12}" cy="388" r="5" fill="${statusDot}"/>
</svg>`;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

// ── Screenshot generation (backend-aligned shape) ──
function generateScreenshot(client: DemoClient, testId: number, seed: number): ScreenshotResult {
  const h = seededHash(seed + client.id.length * 7 + testId * 13);
  // Outlook desktop clients fail more often
  const isOutlook = client.id.startsWith("outlook_2") || client.id === "outlook_365" || client.id === "windows_mail";
  const failThreshold = isOutlook ? 0.3 : client.id === "ios_dark_mode" ? 0.25 : 0.1;
  const status: ScreenshotResult["status"] = h < failThreshold ? "failed" : "complete";

  return {
    client_name: client.name,
    screenshot_url: generateEmailMockupSvg(client.id, testId, status),
    os: client.os,
    category: client.category,
    status,
  };
}

// ── Test generation (backend-aligned shape) ──
interface TestConfig {
  id: number;
  daysAgo: number;
  provider: string;
  clientIds: string[];
  externalTestId: string;
  seed: number;
}

const ALL_CLIENT_IDS = DEMO_CLIENTS.map((c) => c.id);
const DESKTOP_WEBMAIL_IDS = DEMO_CLIENTS
  .filter((c) => c.category === "desktop" || c.category === "web")
  .map((c) => c.id);

const TEST_CONFIGS: TestConfig[] = [
  { id: 1, daysAgo: 1, provider: "litmus", clientIds: ALL_CLIENT_IDS, externalTestId: "lt_abc123def", seed: 42 },
  { id: 2, daysAgo: 4, provider: "email_on_acid", clientIds: ALL_CLIENT_IDS, externalTestId: "eoa_xyz789ghi", seed: 87 },
  { id: 3, daysAgo: 8, provider: "litmus", clientIds: DESKTOP_WEBMAIL_IDS, externalTestId: "lt_mno456pqr", seed: 15 },
  { id: 4, daysAgo: 13, provider: "email_on_acid", clientIds: ALL_CLIENT_IDS, externalTestId: "eoa_stu012vwx", seed: 63 },
];

function generateTest(config: TestConfig): RenderingTest {
  const screenshots = config.clientIds.map((cid) => {
    const client = DEMO_CLIENTS.find((c) => c.id === cid)!;
    return generateScreenshot(client, config.id, config.seed);
  });

  const completed = screenshots.filter((s) => s.status === "complete").length;

  const created = new Date();
  created.setDate(created.getDate() - config.daysAgo);
  created.setHours(10 + (config.seed % 6), (config.seed * 7) % 60, 0, 0);

  return {
    id: config.id,
    external_test_id: config.externalTestId,
    provider: config.provider,
    status: "complete",
    build_id: config.id,
    template_version_id: null,
    clients_requested: config.clientIds.length,
    clients_completed: completed,
    screenshots,
    created_at: created.toISOString(),
  };
}

export const DEMO_RENDERING_TESTS: RenderingTest[] = TEST_CONFIGS.map(generateTest);

// ── Comparisons (test 1 vs test 3 for shared clients) ──
const SHARED_CLIENTS = DEMO_CLIENTS.filter((c) =>
  DESKTOP_WEBMAIL_IDS.includes(c.id),
).slice(0, 5);

export const DEMO_RENDERING_COMPARISON: RenderingComparisonResponse = {
  baseline_test_id: 3,
  current_test_id: 1,
  total_clients: SHARED_CLIENTS.length,
  regressions_found: SHARED_CLIENTS.filter((c) => {
    const h = seededHash(c.id.length * 31 + 7);
    return h * 15 > 5;
  }).length,
  diffs: SHARED_CLIENTS.map((c): RenderingDiff => {
    const h = seededHash(c.id.length * 31 + 7);
    const diff = Math.round(h * 15 * 100) / 100;
    return {
      client_name: c.name,
      diff_percentage: diff,
      has_regression: diff > 5,
      baseline_url: generateEmailMockupSvg(c.id, 3, "complete"),
      current_url: generateEmailMockupSvg(c.id, 1, "complete"),
    };
  }),
};
