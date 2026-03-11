export interface GraphEntity {
  id: string;
  name: string;
  entity_type: string;
  description: string;
  properties: Record<string, unknown>;
}

export interface GraphRelationship {
  source_id: string;
  target_id: string;
  relationship_type: string;
  properties: Record<string, unknown>;
}

export interface GraphSearchResult {
  content: string;
  entities: GraphEntity[];
  relationships: GraphRelationship[];
  score: number;
}

export interface GraphSearchResponse {
  results: GraphSearchResult[];
  query: string;
  mode: "chunks" | "completion";
}

export type SearchMode = "text" | "graph" | "ask";

export interface GraphSearchArgs {
  query: string;
  dataset_name?: string;
  top_k?: number;
  mode?: "chunks" | "completion";
}
