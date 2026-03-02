export interface KnowledgeTag {
  id: number;
  name: string;
  created_at: string;
}

export interface KnowledgeDocument {
  id: number;
  filename: string;
  title: string | null;
  description: string | null;
  domain: string;
  source_type: string;
  language: string;
  file_size_bytes: number | null;
  status: string;
  error_message: string | null;
  chunk_count: number;
  metadata_json: string | null;
  ocr_applied: boolean;
  tags: KnowledgeTag[];
  has_file: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSearchResult {
  chunk_content: string;
  document_id: number;
  document_filename: string;
  domain: string;
  language: string;
  chunk_index: number;
  score: number;
  metadata_json: string | null;
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  query: string;
  total_candidates: number;
  reranked: boolean;
}

export interface KnowledgeDocumentChunk {
  chunk_index: number;
  content: string;
}

export interface KnowledgeDocumentContent {
  document_id: number;
  filename: string;
  title: string | null;
  total_chunks: number;
  chunks: KnowledgeDocumentChunk[];
}

export interface KnowledgeDomainList {
  domains: string[];
  total: number;
}

export interface KnowledgeTagList {
  tags: KnowledgeTag[];
  total: number;
}

export interface PaginatedDocuments {
  items: KnowledgeDocument[];
  total: number;
  page: number;
  page_size: number;
}
