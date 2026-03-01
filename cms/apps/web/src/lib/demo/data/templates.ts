import type { TemplateResponse, VersionResponse } from "@/types/templates";
import {
  SPRING_SALE_HERO_HTML,
  SPRING_SALE_REMINDER_HTML,
  SPRING_SALE_LAST_CHANCE_HTML,
  VALENTINES_PROMO_HTML,
  VALENTINES_GIFT_GUIDE_HTML,
  WELCOME_EMAIL_1_HTML,
  WELCOME_EMAIL_2_HTML,
  SUMMER_PREVIEW_HTML,
} from "./html-sources";

export const DEMO_TEMPLATES: TemplateResponse[] = [
  // ── Project 1: Q1 Spring Sale ──
  {
    id: 1,
    project_id: 1,
    name: "Spring Sale Hero",
    description: "Primary hero announcement for the Q1 spring sale campaign. Full-width hero image with product showcase.",
    subject_line: "Spring Into Savings — Up to 40% Off",
    preheader_text: "Fresh styles, vibrant colours, unbeatable prices. Shop now before they're gone.",
    status: "active",
    created_by_id: 1,
    latest_version: 3,
    created_at: "2026-01-18T10:00:00Z",
    updated_at: "2026-02-15T14:30:00Z",
  },
  {
    id: 2,
    project_id: 1,
    name: "Spring Sale Reminder",
    description: "Follow-up reminder sent 5 days before sale ends. Urgency-focused copy.",
    subject_line: "Don't Miss Out — Spring Sale Ends Soon",
    preheader_text: "Your favourite spring styles are selling fast.",
    status: "active",
    created_by_id: 1,
    latest_version: 2,
    created_at: "2026-01-25T11:00:00Z",
    updated_at: "2026-02-10T09:15:00Z",
  },
  {
    id: 3,
    project_id: 1,
    name: "Spring Sale Last Chance",
    description: "Final-hours urgency email. Bold red design with countdown messaging.",
    subject_line: "FINAL HOURS — Spring Sale Ends Tonight",
    preheader_text: "Last chance to save up to 40%. Sale ends at midnight.",
    status: "draft",
    created_by_id: 1,
    latest_version: 1,
    created_at: "2026-02-01T14:00:00Z",
    updated_at: "2026-02-05T16:45:00Z",
  },
  // ── Project 2: Valentine's Day ──
  {
    id: 4,
    project_id: 2,
    name: "Valentine's Day Promo",
    description: "Hero promotion with gift ideas by budget tier. Approved and exported to Braze.",
    subject_line: "Fall in Love With These Deals",
    preheader_text: "Discover the perfect gift for your Valentine. Free gift wrapping on all orders.",
    status: "active",
    created_by_id: 1,
    latest_version: 4,
    created_at: "2026-01-22T09:00:00Z",
    updated_at: "2026-02-12T08:00:00Z",
  },
  {
    id: 5,
    project_id: 2,
    name: "Valentine's Gift Guide",
    description: "Curated gift guide with 'For Her' and 'For Him' sections. Approved.",
    subject_line: "The Ultimate Valentine's Gift Guide",
    preheader_text: "Not sure what to get? We've curated the best gifts for every special person.",
    status: "active",
    created_by_id: 1,
    latest_version: 2,
    created_at: "2026-01-28T10:30:00Z",
    updated_at: "2026-02-11T15:20:00Z",
  },
  // ── Project 3: Welcome Series ──
  {
    id: 6,
    project_id: 3,
    name: "Welcome Email #1",
    description: "First email in welcome automation. 15% discount code with brand introduction.",
    subject_line: "Welcome to Apex Retail — Here's 15% Off",
    preheader_text: "We're thrilled to have you. Here's a welcome gift to get you started.",
    status: "draft",
    created_by_id: 1,
    latest_version: 1,
    created_at: "2026-02-05T11:00:00Z",
    updated_at: "2026-02-20T13:00:00Z",
  },
  {
    id: 7,
    project_id: 3,
    name: "Welcome Email #2 — Product Intro",
    description: "Second welcome email showcasing bestselling products.",
    subject_line: "Discover Our Bestsellers — Curated for You",
    preheader_text: "Here are some of our most-loved products to get you started.",
    status: "draft",
    created_by_id: 1,
    latest_version: 1,
    created_at: "2026-02-08T14:00:00Z",
    updated_at: "2026-02-22T10:30:00Z",
  },
  // ── Project 4: Summer Teaser ──
  {
    id: 8,
    project_id: 4,
    name: "Summer Collection Preview",
    description: "Teaser email for upcoming summer collection launch. Early access signup.",
    subject_line: "Coming Soon — Summer Collection 2026",
    preheader_text: "Sun-ready styles dropping April 1st. Be the first to see what's new.",
    status: "draft",
    created_by_id: 1,
    latest_version: 1,
    created_at: "2026-02-20T15:30:00Z",
    updated_at: "2026-02-22T10:00:00Z",
  },
];

// Map template ID → HTML source for version lookups
const HTML_BY_TEMPLATE: Record<number, string> = {
  1: SPRING_SALE_HERO_HTML,
  2: SPRING_SALE_REMINDER_HTML,
  3: SPRING_SALE_LAST_CHANCE_HTML,
  4: VALENTINES_PROMO_HTML,
  5: VALENTINES_GIFT_GUIDE_HTML,
  6: WELCOME_EMAIL_1_HTML,
  7: WELCOME_EMAIL_2_HTML,
  8: SUMMER_PREVIEW_HTML,
};

function makeVersions(
  templateId: number,
  count: number,
  startDate: string,
): VersionResponse[] {
  const versions: VersionResponse[] = [];
  const base = new Date(startDate);

  for (let v = 1; v <= count; v++) {
    const created = new Date(base.getTime() + (v - 1) * 3 * 24 * 60 * 60 * 1000);
    versions.push({
      id: templateId * 100 + v,
      template_id: templateId,
      version_number: v,
      html_source: HTML_BY_TEMPLATE[templateId] ?? "",
      css_source: null,
      changelog:
        v === 1
          ? "Initial version"
          : `v${v} — ${["Updated hero image", "Refined CTA copy", "Added product section", "Fixed dark mode contrast"][v % 4]}`,
      created_by_id: 1,
      created_at: created.toISOString(),
    });
  }
  return versions;
}

export const DEMO_VERSIONS: VersionResponse[] = [
  ...makeVersions(1, 3, "2026-01-18T10:00:00Z"),
  ...makeVersions(2, 2, "2026-01-25T11:00:00Z"),
  ...makeVersions(3, 1, "2026-02-01T14:00:00Z"),
  ...makeVersions(4, 4, "2026-01-22T09:00:00Z"),
  ...makeVersions(5, 2, "2026-01-28T10:30:00Z"),
  ...makeVersions(6, 1, "2026-02-05T11:00:00Z"),
  ...makeVersions(7, 1, "2026-02-08T14:00:00Z"),
  ...makeVersions(8, 1, "2026-02-20T15:30:00Z"),
];
