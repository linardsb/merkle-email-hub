export interface FailurePatternResponse {
  id: number;
  agent_name: string;
  qa_check: string;
  client_ids: string[];
  description: string;
  workaround: string;
  confidence: number | null;
  run_id: string;
  blueprint_name: string;
  first_seen: string; // ISO 8601 datetime from backend
  last_seen: string; // ISO 8601 datetime from backend
  frequency: number;
}

export interface FailurePatternListResponse {
  items: FailurePatternResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface FailurePatternStats {
  total_patterns: number;
  unique_agents: number;
  unique_checks: number;
  top_agent: string | null;
  top_check: string | null;
}
