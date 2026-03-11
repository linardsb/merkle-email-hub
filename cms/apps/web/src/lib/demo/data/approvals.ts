import type {
  ApprovalResponse,
  FeedbackResponse,
  AuditResponse,
} from "@email-hub/sdk";

export const DEMO_APPROVALS: ApprovalResponse[] = [
  {
    id: 1,
    build_id: 1,
    project_id: 1,
    status: "pending",
    requested_by_id: 1,
    reviewed_by_id: null,
    review_note: null,
    created_at: "2026-02-18T09:00:00Z",
    updated_at: "2026-02-18T09:00:00Z",
  },
  {
    id: 2,
    build_id: 2,
    project_id: 1,
    status: "revision_requested",
    requested_by_id: 1,
    reviewed_by_id: 2,
    review_note: "Two issues need addressing before we can approve.",
    created_at: "2026-02-12T10:00:00Z",
    updated_at: "2026-02-13T14:20:00Z",
  },
  {
    id: 3,
    build_id: 3,
    project_id: 2,
    status: "approved",
    requested_by_id: 1,
    reviewed_by_id: 2,
    review_note: "Brand-aligned, dark mode looks great. Ready for Braze export.",
    created_at: "2026-02-10T11:00:00Z",
    updated_at: "2026-02-11T09:30:00Z",
  },
  {
    id: 4,
    build_id: 4,
    project_id: 2,
    status: "approved",
    requested_by_id: 1,
    reviewed_by_id: 2,
    review_note: null,
    created_at: "2026-02-10T14:00:00Z",
    updated_at: "2026-02-11T10:15:00Z",
  },
  {
    id: 5,
    build_id: 6,
    project_id: 1,
    status: "rejected",
    requested_by_id: 1,
    reviewed_by_id: 2,
    review_note: "CTA button colour doesn't match the spring palette. Needs to use the approved brand green (#4CAF50), not default red.",
    created_at: "2026-02-08T15:00:00Z",
    updated_at: "2026-02-09T11:45:00Z",
  },
  {
    id: 6,
    build_id: 5,
    project_id: 3,
    status: "pending",
    requested_by_id: 1,
    reviewed_by_id: null,
    review_note: null,
    created_at: "2026-02-22T10:30:00Z",
    updated_at: "2026-02-22T10:30:00Z",
  },
];

export const DEMO_FEEDBACK: Record<number, FeedbackResponse[]> = {
  1: [],
  2: [
    {
      id: 1,
      approval_id: 2,
      author_id: 2,
      content: "Hero image needs higher contrast — the text is hard to read on mobile devices. Consider adding a darker overlay or using a solid background colour fallback.",
      feedback_type: "revision",
      created_at: "2026-02-13T14:00:00Z",
    },
    {
      id: 2,
      approval_id: 2,
      author_id: 2,
      content: "Footer is missing the 2026 copyright year update. Still shows 2025.",
      feedback_type: "revision",
      created_at: "2026-02-13T14:10:00Z",
    },
    {
      id: 3,
      approval_id: 2,
      author_id: 1,
      content: "Thanks for the feedback. Will increase overlay opacity to 60% and update the footer copyright. Revised version incoming.",
      feedback_type: "comment",
      created_at: "2026-02-13T15:30:00Z",
    },
  ],
  3: [
    {
      id: 4,
      approval_id: 3,
      author_id: 2,
      content: "Brand-aligned, dark mode looks great. The gift tier sections work beautifully across all test personas.",
      feedback_type: "approval",
      created_at: "2026-02-11T09:30:00Z",
    },
  ],
  4: [
    {
      id: 5,
      approval_id: 4,
      author_id: 2,
      content: "Clean layout, good responsive behaviour. Approved.",
      feedback_type: "approval",
      created_at: "2026-02-11T10:15:00Z",
    },
  ],
  5: [
    {
      id: 6,
      approval_id: 5,
      author_id: 2,
      content: "The CTA button colour (#E4002B) doesn't match the spring campaign palette. We agreed on using brand green (#4CAF50) for all spring CTAs. Please revise.",
      feedback_type: "rejection",
      created_at: "2026-02-09T11:45:00Z",
    },
  ],
  6: [],
};

export const DEMO_AUDIT: Record<number, AuditResponse[]> = {
  1: [
    { id: 1, approval_id: 1, action: "submitted", actor_id: 1, details: "Submitted Spring Sale Hero for client review", created_at: "2026-02-18T09:00:00Z" },
  ],
  2: [
    { id: 2, approval_id: 2, action: "submitted", actor_id: 1, details: "Submitted Spring Sale Reminder for review", created_at: "2026-02-12T10:00:00Z" },
    { id: 3, approval_id: 2, action: "feedback_added", actor_id: 2, details: "Added revision feedback (2 items)", created_at: "2026-02-13T14:10:00Z" },
    { id: 4, approval_id: 2, action: "revision_requested", actor_id: 2, details: "Requested revisions — hero contrast and footer copyright", created_at: "2026-02-13T14:20:00Z" },
  ],
  3: [
    { id: 5, approval_id: 3, action: "submitted", actor_id: 1, details: "Submitted Valentine's Day Promo for review", created_at: "2026-02-10T11:00:00Z" },
    { id: 6, approval_id: 3, action: "approved", actor_id: 2, details: "Approved — ready for Braze export", created_at: "2026-02-11T09:30:00Z" },
  ],
  4: [
    { id: 7, approval_id: 4, action: "submitted", actor_id: 1, details: "Submitted Valentine's Gift Guide for review", created_at: "2026-02-10T14:00:00Z" },
    { id: 8, approval_id: 4, action: "approved", actor_id: 2, details: "Approved", created_at: "2026-02-11T10:15:00Z" },
  ],
  5: [
    { id: 9, approval_id: 5, action: "submitted", actor_id: 1, details: "Submitted Spring Sale Last Chance for review", created_at: "2026-02-08T15:00:00Z" },
    { id: 10, approval_id: 5, action: "rejected", actor_id: 2, details: "Rejected — CTA colour mismatch", created_at: "2026-02-09T11:45:00Z" },
  ],
  6: [
    { id: 11, approval_id: 6, action: "submitted", actor_id: 1, details: "Submitted Welcome Email #1 for review", created_at: "2026-02-22T10:30:00Z" },
  ],
};
