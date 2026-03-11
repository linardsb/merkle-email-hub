export interface AgentSkillInfo {
  name: string;
  skill_file: string | null;
  l3_files: string[];
  has_failure_warnings: boolean;
}

export interface AgentSkillsResponse {
  agents: AgentSkillInfo[];
}
