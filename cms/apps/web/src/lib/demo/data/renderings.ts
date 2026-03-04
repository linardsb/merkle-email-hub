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

// ── Inline SVG email mockup generator ──
function hslColor(h: number, s: number, l: number): string {
  return `hsl(${Math.round(h)},${Math.round(s)}%,${Math.round(l)}%)`;
}

function generateEmailMockupSvg(clientId: string, testId: number, status: RenderingResultStatus): string {
  const seed = clientId.length * 17 + testId * 31;
  const hue = (seededHash(seed) * 360) % 360;
  const isDark = clientId === "ios_dark_mode";
  const isOutlookDesktop = clientId.startsWith("outlook_2") || clientId === "outlook_365" || clientId === "windows_mail";
  const isGmail = clientId.startsWith("gmail") || clientId === "gmail_workspace";
  const isMobile = clientId.startsWith("iphone") || clientId === "ipad_mail" || clientId.includes("android") || clientId === "yahoo_mobile" || clientId === "samsung_mail";

  // Colors
  const pageBg = isDark ? "#121218" : "#f0f0f0";
  const cardBg = isDark ? "#1e1e2a" : "#ffffff";
  const headerBg = hslColor(hue, 65, isDark ? 35 : 45);
  const heroBg = hslColor(hue, 50, isDark ? 25 : 85);
  const textColor = isDark ? "#888899" : "#cccccc";
  const ctaBg = hslColor(hue, 70, isDark ? 45 : 50);
  const footerColor = isDark ? "#555566" : "#dddddd";

  // Layout dimensions
  const cardW = isMobile ? 480 : 520;
  const cardX = (600 - cardW) / 2;
  const heroShift = isOutlookDesktop ? 8 : 0;   // simulate Word engine misalignment
  const heroGap = isOutlookDesktop ? 12 : 0;     // extra gap from layout shift
  const clipLine = isGmail;                       // show clip indicator

  // Status indicator color
  const statusDot = status === "pass" ? "#22c55e" : status === "warning" ? "#eab308" : "#ef4444";

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <rect width="600" height="400" fill="${pageBg}"/>
  <rect x="${cardX}" y="16" width="${cardW}" height="368" rx="4" fill="${cardBg}" stroke="${isDark ? "#2a2a3a" : "#e5e5e5"}" stroke-width="1"/>
  <!-- Header -->
  <rect x="${cardX}" y="16" width="${cardW}" height="44" rx="4" fill="${headerBg}"/>
  <rect x="${cardX + 16}" y="30" width="80" height="16" rx="2" fill="${isDark ? "#ffffff33" : "#ffffff88"}"/>
  <rect x="${cardX + cardW - 96}" y="33" width="60" height="10" rx="2" fill="${isDark ? "#ffffff22" : "#ffffff55"}"/>
  <!-- Hero image area -->
  <rect x="${cardX + 20 + heroShift}" y="${68 + heroGap}" width="${cardW - 40}" height="120" rx="3" fill="${heroBg}"/>
  <rect x="${cardX + (cardW / 2) - 60}" y="${108 + heroGap}" width="120" height="14" rx="2" fill="${isDark ? "#ffffff18" : "#00000012"}"/>
  <rect x="${cardX + (cardW / 2) - 40}" y="${128 + heroGap}" width="80" height="10" rx="2" fill="${isDark ? "#ffffff10" : "#00000008"}"/>
  <!-- Body text lines -->
  <rect x="${cardX + 24}" y="${200 + heroGap}" width="${cardW - 48}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${216 + heroGap}" width="${cardW - 80}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${232 + heroGap}" width="${cardW - 60}" height="8" rx="2" fill="${textColor}"/>
  <rect x="${cardX + 24}" y="${248 + heroGap}" width="${cardW - 100}" height="8" rx="2" fill="${textColor}"/>
  <!-- CTA button -->
  <rect x="${cardX + (cardW / 2) - 60}" y="${270 + heroGap}" width="120" height="32" rx="4" fill="${ctaBg}"/>
  <rect x="${cardX + (cardW / 2) - 30}" y="${282 + heroGap}" width="60" height="8" rx="2" fill="#ffffffcc"/>
  <!-- Footer -->
  <rect x="${cardX + 24}" y="${318 + heroGap}" width="${cardW - 48}" height="1" fill="${footerColor}"/>
  <rect x="${cardX + (cardW / 2) - 70}" y="${328 + heroGap}" width="140" height="6" rx="1" fill="${footerColor}"/>
  <rect x="${cardX + (cardW / 2) - 50}" y="${340 + heroGap}" width="100" height="6" rx="1" fill="${footerColor}"/>
  ${clipLine ? `<!-- Gmail clip line -->
  <line x1="${cardX + 10}" y1="350" x2="${cardX + cardW - 10}" y2="350" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.6"/>
  <text x="${cardX + cardW - 16}" y="348" font-size="8" fill="#ef4444" text-anchor="end" opacity="0.6" font-family="sans-serif">clipped</text>` : ""}
  <!-- Status dot -->
  <circle cx="${cardX + cardW - 12}" cy="400 - 12" r="5" fill="${statusDot}"/>
</svg>`;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

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
    screenshot_url: generateEmailMockupSvg(clientId, testId, resultStatusFromIssues(issues)),
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
    baseline_url: generateEmailMockupSvg(cid, 3, "pass"),
    current_url: generateEmailMockupSvg(cid, 1, "pass"),
    diff_percentage: diff,
    status: diff < 1 ? "identical" : diff < 5 ? "minor_diff" : "major_diff",
  };
});
