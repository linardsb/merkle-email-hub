import type { ProjectResponse } from "@email-hub/sdk";

export const DEMO_PROJECTS: ProjectResponse[] = [
  {
    id: 1,
    name: "Q1 Spring Sale Campaign",
    description:
      "Multi-touch spring sale campaign targeting existing customers. Includes hero announcement, reminder, and last-chance urgency emails with progressive discount tiers.",
    client_org_id: 1,
    status: "active",
    created_by_id: 1,
    is_active: true,
    target_clients: ["gmail_web", "outlook_365_win", "apple_mail_ios", "outlook_2019_win", "gmail_android"],
    created_at: "2026-01-15T09:00:00Z",
    updated_at: "2026-02-20T16:45:00Z",
  },
  {
    id: 2,
    name: "Valentine's Day Flash Promo",
    description:
      "Time-sensitive Valentine's Day promotion with gift guide and flash sale. Completed and exported to Braze.",
    client_org_id: 1,
    status: "active",
    created_by_id: 1,
    is_active: true,
    target_clients: ["gmail_web", "apple_mail_ios", "apple_mail_macos"],
    created_at: "2026-01-20T10:30:00Z",
    updated_at: "2026-02-14T23:59:00Z",
  },
  {
    id: 3,
    name: "New Customer Welcome Series",
    description:
      "3-email automated welcome sequence for new subscribers. Introduces brand, showcases top products, and offers first-purchase discount.",
    client_org_id: 1,
    status: "draft",
    created_by_id: 1,
    is_active: true,
    target_clients: ["gmail_web", "outlook_365_win", "apple_mail_ios", "outlook_web", "yahoo_web", "samsung_mail"],
    created_at: "2026-02-01T11:00:00Z",
    updated_at: "2026-02-25T14:20:00Z",
  },
  {
    id: 4,
    name: "Summer Collection Teaser",
    description:
      "Early teaser campaign for the upcoming summer collection. Single template in planning phase.",
    client_org_id: 1,
    status: "draft",
    created_by_id: 1,
    is_active: true,
    created_at: "2026-02-20T15:00:00Z",
    updated_at: "2026-02-22T10:30:00Z",
  },
];
