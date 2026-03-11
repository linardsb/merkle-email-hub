/**
 * Graph search types — re-exported from SDK where available.
 * Frontend-only UI types kept locally.
 */
export type {
  GraphEntityResponse as GraphEntity,
  GraphRelationshipResponse as GraphRelationship,
  GraphSearchResultResponse as GraphSearchResult,
  GraphSearchResponse,
  GraphSearchRequest,
} from "@email-hub/sdk";

/** Frontend-only: search mode toggle (maps to SDK's GraphSearchRequest.mode) */
export type SearchMode = "text" | "graph" | "ask";

/** Frontend-only: hook arguments for graph search */
export interface GraphSearchArgs {
  query: string;
  dataset_name?: string;
  top_k?: number;
  mode?: "chunks" | "completion";
}
