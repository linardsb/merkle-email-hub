"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type {
  KnowledgeSearchResponse,
  PaginatedDocuments,
  KnowledgeDocument,
  KnowledgeDocumentContent,
  KnowledgeDomainList,
  KnowledgeTagList,
} from "@/types/knowledge";

// ── Browse documents (GET) ──

interface UseKnowledgeDocumentsOptions {
  page?: number;
  pageSize?: number;
  domain?: string;
  tag?: string;
}

export function useKnowledgeDocuments(
  options: UseKnowledgeDocumentsOptions = {},
) {
  const { page = 1, pageSize = 12, domain, tag } = options;

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (domain) params.set("domain", domain);
  if (tag) params.set("tag", tag);

  return useSWR<PaginatedDocuments>(
    `/api/v1/knowledge/documents?${params.toString()}`,
    fetcher,
  );
}

export function useKnowledgeDocument(documentId: number | null) {
  return useSWR<KnowledgeDocument>(
    documentId ? `/api/v1/knowledge/documents/${documentId}` : null,
    fetcher,
  );
}

export function useKnowledgeDocumentContent(documentId: number | null) {
  return useSWR<KnowledgeDocumentContent>(
    documentId ? `/api/v1/knowledge/documents/${documentId}/content` : null,
    fetcher,
  );
}

// ── Domains & Tags (GET) ──

export function useKnowledgeDomains() {
  return useSWR<KnowledgeDomainList>(
    "/api/v1/knowledge/domains",
    fetcher,
  );
}

export function useKnowledgeTags() {
  return useSWR<KnowledgeTagList>("/api/v1/knowledge/tags", fetcher);
}

// ── Search (POST via useSWRMutation) ──

interface SearchArg {
  query: string;
  domain?: string;
  limit?: number;
}

export function useKnowledgeSearch() {
  return useSWRMutation<KnowledgeSearchResponse, Error, string, SearchArg>(
    "/api/v1/knowledge/search",
    mutationFetcher,
  );
}
