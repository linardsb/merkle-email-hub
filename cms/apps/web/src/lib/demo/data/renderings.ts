import type {
  RenderingClient,
  RenderingTest,
  RenderingResult,
  RenderingComparison,
  RenderingIssue,
  RenderingResultStatus,
  RenderingProvider,
} from "@/types/rendering";

// ── Seeded hash (same as qa-results.ts) ──
function seededHash(seed: number): number {
  return ((seed * 2654435761) >>> 0) / 4294967296;
}

// ── 25 Email Clients ──
export const DEMO_RENDERING_CLIENTS: RenderingClient[] = [
  // Desktop (7)
  { id: "outlook_2016", name: "Outlook 2016", category: "desktop", platform: "windows", market_share: 5.2 },
  { id: "outlook_2019", name: "Outlook 2019", category: "desktop", platform: "windows", market_share: 8.7 },
  { id: "outlook_365", name: "Outlook 365", category: "desktop", platform: "windows", market_share: 12.1 },
  { id: "outlook_mac", name: "Outlook Mac", category: "desktop", platform: "macos", market_share: 3.4 },
  { id: "apple_mail_macos", name: "Apple Mail macOS", category: "desktop", platform: "macos", market_share: 7.8 },
  { id: "thunderbird", name: "Thunderbird", category: "desktop", platform: "linux", market_share: 1.2 },
  { id: "windows_mail", name: "Windows Mail", category: "desktop", platform: "windows", market_share: 2.1 },
  // Webmail (8)
  { id: "gmail_web", name: "Gmail", category: "webmail", platform: "web", market_share: 27.6 },
  { id: "yahoo_web", name: "Yahoo Mail", category: "webmail", platform: "web", market_share: 3.8 },
  { id: "outlook_com", name: "Outlook.com", category: "webmail", platform: "web", market_share: 6.5 },
  { id: "aol_web", name: "AOL Mail", category: "webmail", platform: "web", market_share: 1.1 },
  { id: "protonmail", name: "ProtonMail", category: "webmail", platform: "web", market_share: 0.9 },
  { id: "fastmail", name: "Fastmail", category: "webmail", platform: "web", market_share: 0.4 },
  { id: "gmail_workspace", name: "Gmail Workspace", category: "webmail", platform: "web", market_share: 4.2 },
  { id: "zoho_mail", name: "Zoho Mail", category: "webmail", platform: "web", market_share: 0.6 },
  // Mobile (10)
  { id: "iphone_16", name: "iPhone 16 Mail", category: "mobile", platform: "ios", market_share: 8.3 },
  { id: "iphone_15", name: "iPhone 15 Mail", category: "mobile", platform: "ios", market_share: 6.1 },
  { id: "ipad_mail", name: "iPad Mail", category: "mobile", platform: "ios", market_share: 3.5 },
  { id: "gmail_android", name: "Gmail Android", category: "mobile", platform: "android", market_share: 5.4 },
  { id: "gmail_ios", name: "Gmail iOS", category: "mobile", platform: "ios", market_share: 4.7 },
  { id: "samsung_mail", name: "Samsung Mail", category: "mobile", platform: "android", market_share: 3.2 },
  { id: "outlook_ios", name: "Outlook iOS", category: "mobile", platform: "ios", market_share: 2.8 },
  { id: "outlook_android", name: "Outlook Android", category: "mobile", platform: "android", market_share: 2.3 },
  { id: "yahoo_mobile", name: "Yahoo Mobile", category: "mobile", platform: "android", market_share: 1.4 },
  { id: "ios_dark_mode", name: "iOS Dark Mode", category: "mobile", platform: "ios", market_share: 4.9 },
];

// ── Issue templates per client type ──
const OUTLOOK_ISSUES: RenderingIssue[] = [
  { type: "missing_background", severity: "critical", description: "VML background image not rendering in Word rendering engine", affected_area: "Hero section" },
  { type: "layout_shift", severity: "major", description: "Table width collapsed in 120 DPI mode", affected_area: "Content grid" },
  { type: "spacing_mismatch", severity: "minor", description: "Padding inconsistent due to Word engine box model", affected_area: "Footer" },
  { type: "font_fallback", severity: "minor", description: "Custom web font replaced with Times New Roman", affected_area: "Body text" },
];

const GMAIL_ISSUES: RenderingIssue[] = [
  { type: "clipped_content", severity: "critical", description: "Email clipped at 102KB threshold — footer and unsubscribe link hidden", affected_area: "Below fold" },
  { type: "clipped_content", severity: "major", description: "Embedded CSS <style> block stripped by Gmail", affected_area: "Global styles" },
  { type: "image_blocking", severity: "minor", description: "Images blocked by default — no alt text visible", affected_area: "Hero image" },
];

const DARK_MODE_ISSUES: RenderingIssue[] = [
  { type: "dark_mode_inversion", severity: "critical", description: "Background color inverted without color-scheme meta tag", affected_area: "Full email" },
  { type: "dark_mode_inversion", severity: "major", description: "Logo transparency causes white-on-white in dark mode", affected_area: "Header logo" },
  { type: "dark_mode_inversion", severity: "minor", description: "Light text on light background in dark mode CTA button", affected_area: "CTA button" },
];

const MOBILE_ISSUES: RenderingIssue[] = [
  { type: "alignment_error", severity: "minor", description: "Two-column layout not stacking on small viewport", affected_area: "Product grid" },
  { type: "spacing_mismatch", severity: "minor", description: "Touch target too small for mobile CTA button", affected_area: "CTA button" },
];

// ── Result generation ──
function getIssuesForClient(clientId: string, seed: number): RenderingIssue[] {
  const issues: RenderingIssue[] = [];
  const h = seededHash(seed);

  if (clientId.startsWith("outlook_2") || clientId === "outlook_365" || clientId === "windows_mail") {
    // Outlook desktop: high fail rate
    if (h < 0.4) issues.push(OUTLOOK_ISSUES[seed % OUTLOOK_ISSUES.length]!);
    if (h < 0.2) issues.push(OUTLOOK_ISSUES[(seed + 1) % OUTLOOK_ISSUES.length]!);
  } else if (clientId.startsWith("gmail") || clientId === "gmail_workspace") {
    // Gmail: medium warn rate
    if (h < 0.25) issues.push(GMAIL_ISSUES[seed % GMAIL_ISSUES.length]!);
  } else if (clientId === "ios_dark_mode") {
    // Dark mode: specific issues
    if (h < 0.35) issues.push(DARK_MODE_ISSUES[seed % DARK_MODE_ISSUES.length]!);
  } else if (clientId.startsWith("iphone") || clientId === "ipad_mail") {
    // iOS: mostly pass
    if (h < 0.08) issues.push(MOBILE_ISSUES[seed % MOBILE_ISSUES.length]!);
  } else {
    // Others: low-medium issue rate
    if (h < 0.15) issues.push(MOBILE_ISSUES[seed % MOBILE_ISSUES.length]!);
  }

  return issues;
}

function resultStatusFromIssues(issues: RenderingIssue[]): RenderingResultStatus {
  if (issues.some((i) => i.severity === "critical")) return "fail";
  if (issues.some((i) => i.severity === "major")) return "warning";
  if (issues.length > 0) return "warning";
  return "pass";
}

function generateResult(clientId: string, testId: number, seedBase: number): RenderingResult {
  const seed = seedBase + clientId.length * 7 + testId * 13;
  const issues = getIssuesForClient(clientId, seed);
  const loadTime = 800 + Math.floor(seededHash(seed + 99) * 2200);

  return {
    client_id: clientId,
    status: resultStatusFromIssues(issues),
    screenshot_url: `https://picsum.photos/seed/${clientId}-${testId}/600/400`,
    load_time_ms: loadTime,
    issues,
  };
}

function computeCompatScore(results: RenderingResult[]): number {
  if (results.length === 0) return 0;
  const passCount = results.filter((r) => r.status === "pass").length;
  const warnCount = results.filter((r) => r.status === "warning").length;
  return Math.round(((passCount + warnCount * 0.5) / results.length) * 100);
}

// ── Test generation ──
interface TestConfig {
  id: number;
  daysAgo: number;
  provider: RenderingProvider;
  clientIds: string[];
  templateName: string;
  seed: number;
}

const ALL_CLIENT_IDS = DEMO_RENDERING_CLIENTS.map((c) => c.id);
const DESKTOP_WEBMAIL_IDS = DEMO_RENDERING_CLIENTS
  .filter((c) => c.category === "desktop" || c.category === "webmail")
  .map((c) => c.id);

const TEST_CONFIGS: TestConfig[] = [
  { id: 1, daysAgo: 1, provider: "litmus", clientIds: ALL_CLIENT_IDS, templateName: "Spring Sale Hero", seed: 42 },
  { id: 2, daysAgo: 4, provider: "email_on_acid", clientIds: ALL_CLIENT_IDS, templateName: "Welcome Series v3", seed: 87 },
  { id: 3, daysAgo: 8, provider: "litmus", clientIds: DESKTOP_WEBMAIL_IDS, templateName: "Monthly Newsletter", seed: 15 },
  { id: 4, daysAgo: 13, provider: "email_on_acid", clientIds: ALL_CLIENT_IDS, templateName: "Flash Promo Banner", seed: 63 },
];

function generateTest(config: TestConfig): RenderingTest {
  const results = config.clientIds.map((cid) => generateResult(cid, config.id, config.seed));
  const score = computeCompatScore(results);

  const created = new Date();
  created.setDate(created.getDate() - config.daysAgo);
  created.setHours(10 + (config.seed % 6), (config.seed * 7) % 60, 0, 0);

  const completed = new Date(created);
  completed.setMinutes(completed.getMinutes() + 3 + (config.seed % 5));

  return {
    id: config.id,
    build_id: config.id,
    template_name: config.templateName,
    provider: config.provider,
    status: "completed",
    clients_requested: config.clientIds,
    results,
    compatibility_score: score,
    created_at: created.toISOString(),
    completed_at: completed.toISOString(),
  };
}

export const DEMO_RENDERING_TESTS: RenderingTest[] = TEST_CONFIGS.map(generateTest);

// ── Comparisons (test 1 vs test 3 for shared clients) ──
const SHARED_COMPARISON_CLIENTS = DESKTOP_WEBMAIL_IDS.slice(0, 5);

export const DEMO_RENDERING_COMPARISONS: RenderingComparison[] = SHARED_COMPARISON_CLIENTS.map((cid) => {
  const h = seededHash(cid.length * 31 + 7);
  const diff = Math.round(h * 15 * 100) / 100;
  return {
    test_id_baseline: 3,
    test_id_current: 1,
    client_id: cid,
    baseline_url: `https://picsum.photos/seed/${cid}-3/600/400`,
    current_url: `https://picsum.photos/seed/${cid}-1/600/400`,
    diff_percentage: diff,
    status: diff < 1 ? "identical" : diff < 5 ? "minor_diff" : "major_diff",
  };
});
