import type {
  FailurePatternResponse,
  FailurePatternStats,
} from "@/types/failure-patterns";

export const DEMO_FAILURE_PATTERNS: FailurePatternResponse[] = [
  {
    id: 1,
    agent_name: "scaffolder",
    qa_check: "css_support",
    client_ids: ["outlook_2016", "outlook_2019"],
    description:
      "[failure_pattern] Agent 'scaffolder' failed QA check 'css_support' during blueprint 'campaign'. Target email clients: outlook_2016, outlook_2019. Issue: CSS property 'flex-direction' not supported in Outlook desktop clients (score=0.4)",
    workaround:
      "Use table-based layout instead of flexbox for Outlook compatibility",
    confidence: 0.35,
    run_id: "run-fp-001",
    blueprint_name: "campaign",
    first_seen: "2026-03-01T10:00:00Z",
    last_seen: "2026-03-10T14:30:00Z",
    frequency: 5,
  },
  {
    id: 2,
    agent_name: "dark_mode",
    qa_check: "dark_mode",
    client_ids: ["outlook_2016", "outlook_2019", "windows_mail"],
    description:
      "[failure_pattern] Agent 'dark_mode' failed QA check 'dark_mode' during blueprint 'campaign'. Issue: Missing color-scheme meta tag and prefers-color-scheme media query for Outlook dark mode (score=0.3)",
    workaround:
      'Add <meta name="color-scheme" content="light dark"> and [data-ogsc] selectors for Outlook',
    confidence: 0.42,
    run_id: "run-fp-002",
    blueprint_name: "campaign",
    first_seen: "2026-03-02T09:15:00Z",
    last_seen: "2026-03-09T16:45:00Z",
    frequency: 4,
  },
  {
    id: 3,
    agent_name: "outlook_fixer",
    qa_check: "fallback",
    client_ids: ["outlook_2016"],
    description:
      "[failure_pattern] Agent 'outlook_fixer' failed QA check 'fallback'. Issue: MSO conditional comments missing for background image VML fallback (score=0.5)",
    workaround:
      "Wrap background images in <!--[if gte mso 9]> VML markup",
    confidence: 0.55,
    run_id: "run-fp-003",
    blueprint_name: "campaign",
    first_seen: "2026-03-03T11:20:00Z",
    last_seen: "2026-03-08T13:10:00Z",
    frequency: 3,
  },
  {
    id: 4,
    agent_name: "content",
    qa_check: "spam_score",
    client_ids: ["gmail", "yahoo_mail"],
    description:
      "[failure_pattern] Agent 'content' failed QA check 'spam_score'. Issue: Subject line contains common spam trigger words: 'FREE', 'ACT NOW' (score=0.6)",
    workaround:
      "Avoid all-caps trigger words; rephrase offers naturally",
    confidence: 0.65,
    run_id: "run-fp-004",
    blueprint_name: "campaign",
    first_seen: "2026-03-05T08:45:00Z",
    last_seen: "2026-03-10T10:20:00Z",
    frequency: 2,
  },
  {
    id: 5,
    agent_name: "scaffolder",
    qa_check: "html_validation",
    client_ids: ["apple_mail_18", "ios_mail_18"],
    description:
      "[failure_pattern] Agent 'scaffolder' failed QA check 'html_validation'. Issue: Missing DOCTYPE declaration causes rendering inconsistency in Apple Mail (score=0.7)",
    workaround:
      "Ensure <!DOCTYPE html> is present at the top of the HTML document",
    confidence: 0.48,
    run_id: "run-fp-005",
    blueprint_name: "campaign",
    first_seen: "2026-03-04T14:30:00Z",
    last_seen: "2026-03-07T09:00:00Z",
    frequency: 2,
  },
  {
    id: 6,
    agent_name: "accessibility",
    qa_check: "accessibility",
    client_ids: ["gmail", "apple_mail_18", "outlook_2019"],
    description:
      "[failure_pattern] Agent 'accessibility' failed QA check 'accessibility'. Issue: Images missing alt text attributes, table elements missing role='presentation' (score=0.4)",
    workaround:
      "Add descriptive alt text to all images; add role='presentation' to layout tables",
    confidence: 0.38,
    run_id: "run-fp-006",
    blueprint_name: "campaign",
    first_seen: "2026-03-06T12:00:00Z",
    last_seen: "2026-03-10T11:30:00Z",
    frequency: 3,
  },
  {
    id: 7,
    agent_name: "code_reviewer",
    qa_check: "file_size",
    client_ids: ["gmail"],
    description:
      "[failure_pattern] Agent 'code_reviewer' failed QA check 'file_size'. Issue: HTML exceeds Gmail 102KB clipping threshold at 118KB (score=0.2)",
    workaround:
      "Remove redundant CSS, inline only used styles, compress images",
    confidence: 0.72,
    run_id: "run-fp-007",
    blueprint_name: "campaign",
    first_seen: "2026-03-07T15:20:00Z",
    last_seen: "2026-03-10T08:45:00Z",
    frequency: 2,
  },
];

export const DEMO_FAILURE_PATTERN_STATS: FailurePatternStats = {
  total_patterns: 7,
  unique_agents: 5,
  unique_checks: 6,
  top_agent: "scaffolder",
  top_check: "css_support",
};
