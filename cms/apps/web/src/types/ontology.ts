/**
 * Ontology & Competitive Intelligence types.
 * Local interfaces matching backend schemas (app/knowledge/ontology/schemas.py).
 */

export interface EmailClientSchema {
  id: string;
  name: string;
  family: string;
  platform: string;
  engine: string;
  market_share: number;
}

export interface ChangelogEntry {
  property_id: string;
  client_id: string;
  old_level: string | null;
  new_level: string;
  source: string;
}

export interface SyncReportResponse {
  new_properties: number;
  updated_levels: number;
  new_clients: number;
  changelog: ChangelogEntry[];
  errors: string[];
  dry_run: boolean;
  commit_sha: string;
}

export interface SyncStatusResponse {
  last_sync_at: string | null;
  last_commit_sha: string | null;
  features_synced: number;
  error_count: number;
  last_report: Record<string, unknown> | null;
}

export interface CapabilityFeasibility {
  id: string;
  name: string;
  category: string;
  audience_coverage: number;
  blocking_clients: string[];
  hub_supports: boolean;
  hub_agent: string;
  competitor_names: string[];
}

export interface CompetitiveReportResponse {
  audience_client_ids: string[];
  total_capabilities: number;
  hub_advantages: CapabilityFeasibility[];
  gaps: CapabilityFeasibility[];
  opportunities: CapabilityFeasibility[];
  full_matrix: CapabilityFeasibility[];
}
