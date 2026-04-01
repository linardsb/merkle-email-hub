/**
 * Centralized SWR configuration constants.
 * Single source of truth for polling intervals, deduplication, and stale times.
 */

/** Polling intervals (ms). Used with refreshInterval or useSmartPolling. */
export const POLL = {
  /** Real-time: rendering tests, active builds, design sync imports */
  realtime: 3_000,
  /** Frequent: QA reports, blueprint runs, active workflows */
  frequent: 5_000,
  /** Moderate: MCP connections, agent status */
  moderate: 15_000,
  /** Status: MCP status, voice briefs, inactive workflows */
  status: 30_000,
  /** Background: plugins, ontology, penpot, workflow lists */
  background: 60_000,
  /** Disabled */
  off: 0,
} as const;

/** Deduplication intervals (ms). Prevents duplicate requests within window. */
export const DEDUP = {
  /** Standard deduplication — global default */
  standard: 5_000,
  /** Reference data — email clients, ontology (5 min) */
  reference: 300_000,
  /** Very static data — agent skills, compatibility briefs (10 min) */
  static: 600_000,
} as const;

/** SWR option presets for common patterns. Spread into useSWR options. */
export const SWR_PRESETS = {
  /** Polling endpoint: no focus revalidation (polling handles freshness) */
  polling: {
    dedupingInterval: DEDUP.standard,
    revalidateOnFocus: false,
  },
  /** Static/reference data: long dedup, no focus/reconnect revalidation */
  static: {
    dedupingInterval: DEDUP.static,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  },
  /** Reference data: medium dedup, no focus revalidation */
  reference: {
    dedupingInterval: DEDUP.reference,
    revalidateOnFocus: false,
  },
  /** User-triggered: revalidate on focus, standard dedup */
  interactive: {
    dedupingInterval: DEDUP.standard,
    revalidateOnFocus: true,
  },
} as const;
