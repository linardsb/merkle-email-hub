import type { QAResultResponse, QACheckResult } from "@/types/qa";

const CHECK_NAMES = [
  "html_validation",
  "css_support",
  "file_size",
  "link_validation",
  "spam_score",
  "dark_mode",
  "accessibility",
  "fallback",
  "image_optimization",
  "brand_compliance",
] as const;

type CheckName = (typeof CHECK_NAMES)[number];

// Failure message templates per check
const FAILURE_MESSAGES: Record<CheckName, string[]> = {
  html_validation: ["Missing DOCTYPE declaration", "Unclosed <td> tag on line 45"],
  css_support: [
    "CSS property 'gap' not supported in Outlook 2019",
    "CSS property 'border-radius' partially supported in Gmail",
    "CSS shorthand 'background' stripped in Yahoo Mail",
  ],
  file_size: ["Email HTML is 108KB — exceeds Gmail's 102KB clipping threshold"],
  link_validation: ["Link 'http://example.com/old' uses HTTP instead of HTTPS"],
  spam_score: [
    "Subject line contains spam trigger word: 'FREE'",
    "Excessive use of capitalisation in subject line",
  ],
  dark_mode: [
    "Missing color-scheme meta tag",
    "No prefers-color-scheme media query detected",
    "Missing [data-ogsc] Outlook dark mode selectors",
  ],
  accessibility: [
    "2 images missing alt attributes",
    "Missing lang attribute on <html> element",
    "Table used for layout without role='presentation'",
  ],
  fallback: [
    "No MSO conditional comments detected for Outlook fallbacks",
    "Missing VML namespace declaration",
  ],
  image_optimization: [
    "Image 'hero.jpg' missing explicit width/height attributes",
    "Large image detected: 'banner.png' is 450KB",
  ],
  brand_compliance: [
    "CTA colour #0066cc doesn't match brand guidelines (#E4002B)",
    "Font fallback chain doesn't include approved brand fonts",
  ],
};

// Generate a deterministic but varied score for a check
function checkResult(
  checkName: CheckName,
  seed: number,
): QACheckResult {
  // Each check has a different base pass rate
  const passRates: Record<CheckName, number> = {
    html_validation: 0.92,
    css_support: 0.7,
    file_size: 0.95,
    link_validation: 0.9,
    spam_score: 0.88,
    dark_mode: 0.55,
    accessibility: 0.65,
    fallback: 0.85,
    image_optimization: 0.8,
    brand_compliance: 0.9,
  };

  // Seeded "random" using a simple hash
  const hash = ((seed * 2654435761) >>> 0) / 4294967296;
  const passed = hash < passRates[checkName];
  const score = passed ? 1 : 0;
  const messages = FAILURE_MESSAGES[checkName];
  const details = passed ? null : messages[seed % messages.length];

  return {
    check_name: checkName,
    passed,
    score,
    details,
    severity: passed ? "info" : checkName === "file_size" ? "error" : "warning",
  };
}

function generateResult(
  id: number,
  daysAgo: number,
  seed: number,
  overrideId?: number,
): QAResultResponse {
  const checks = CHECK_NAMES.map((name, i) => checkResult(name, seed + i));
  const checksPassed = checks.filter((c) => c.passed).length;
  const checksTotal = checks.length;
  const overallScore = checksPassed / checksTotal;
  const passed = overallScore >= 0.7;

  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  date.setHours(9 + (seed % 8), (seed * 17) % 60, 0, 0);

  const result: QAResultResponse = {
    id,
    build_id: ((id - 1) % 6) + 1,
    template_version_id: ((id - 1) % 8) * 100 + 1,
    overall_score: overallScore,
    passed,
    checks_passed: checksPassed,
    checks_total: checksTotal,
    checks,
    override: overrideId
      ? {
          id: overrideId,
          qa_result_id: id,
          overridden_by_id: 1,
          justification: "Client-approved exception — brand compliance check is pending updated guidelines.",
          checks_overridden: checks.filter((c) => !c.passed).map((c) => c.check_name),
          created_at: date.toISOString(),
        }
      : null,
    created_at: date.toISOString(),
  };

  return result;
}

// Generate 25 QA results spanning 30 days
export const DEMO_QA_RESULTS: QAResultResponse[] = [
  // Recent results (last 7 days)
  generateResult(1, 1, 42),
  generateResult(2, 1, 87),
  generateResult(3, 2, 15),
  generateResult(4, 3, 63),
  generateResult(5, 3, 29),
  generateResult(6, 4, 91),
  generateResult(7, 5, 7),
  generateResult(8, 6, 55),

  // Mid-range (8-15 days ago)
  generateResult(9, 8, 33),
  generateResult(10, 9, 71),
  generateResult(11, 10, 48, 1), // overridden
  generateResult(12, 11, 12),
  generateResult(13, 12, 66),
  generateResult(14, 13, 24),
  generateResult(15, 14, 88),

  // Older (16-30 days ago)
  generateResult(16, 16, 5),
  generateResult(17, 18, 39),
  generateResult(18, 20, 77, 2), // overridden
  generateResult(19, 21, 51),
  generateResult(20, 23, 18),
  generateResult(21, 24, 94),
  generateResult(22, 25, 60),
  generateResult(23, 27, 36),
  generateResult(24, 28, 82),
  generateResult(25, 30, 45),
];
