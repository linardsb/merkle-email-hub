// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

vi.mock("@/lib/swr-fetcher", () => ({ fetcher: vi.fn() }));
vi.mock("@/lib/mutation-fetcher", () => ({
  mutationFetcher: vi.fn(),
  longMutationFetcher: vi.fn(),
}));
vi.mock("@/lib/auth-fetch", () => ({ authFetch: vi.fn() }));
vi.mock("@/lib/api-error", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      message: string,
      public code?: string,
    ) {
      super(message);
    }
  },
}));

const mockUseSWR = vi
  .fn()
  .mockReturnValue({ data: undefined, error: undefined, isLoading: true, mutate: vi.fn() });
const mockUseSWRMutation = vi
  .fn()
  .mockReturnValue({ trigger: vi.fn(), isMutating: false });
vi.mock("swr", () => ({ default: (...args: unknown[]) => mockUseSWR(...args) }));
vi.mock("swr/mutation", () => ({ default: (...args: unknown[]) => mockUseSWRMutation(...args) }));

import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher, longMutationFetcher } from "@/lib/mutation-fetcher";

beforeEach(() => {
  mockUseSWR.mockClear();
  mockUseSWRMutation.mockClear();
});

// ─── use-knowledge.ts ───

describe("use-knowledge", () => {
  describe("useKnowledgeDocuments", () => {
    it("passes correct key with defaults", async () => {
      const { useKnowledgeDocuments } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocuments());
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("/api/v1/knowledge/documents?");
      expect(key).toContain("page=1");
      expect(key).toContain("page_size=12");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("includes domain filter when provided", async () => {
      const { useKnowledgeDocuments } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocuments({ domain: "brand" }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("domain=brand");
    });

    it("includes tag filter when provided", async () => {
      const { useKnowledgeDocuments } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocuments({ tag: "footer" }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("tag=footer");
    });
  });

  describe("useKnowledgeDocument", () => {
    it("passes correct key with valid documentId", async () => {
      const { useKnowledgeDocument } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocument(42));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/knowledge/documents/42");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when documentId is null", async () => {
      const { useKnowledgeDocument } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocument(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useKnowledgeDocumentContent", () => {
    it("passes correct key with valid documentId", async () => {
      const { useKnowledgeDocumentContent } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocumentContent(7));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/knowledge/documents/7/content");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when documentId is null", async () => {
      const { useKnowledgeDocumentContent } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDocumentContent(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useKnowledgeDomains", () => {
    it("passes correct key", async () => {
      const { useKnowledgeDomains } = await import("../use-knowledge");
      renderHook(() => useKnowledgeDomains());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/knowledge/domains");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });
  });

  describe("useKnowledgeTags", () => {
    it("passes correct key", async () => {
      const { useKnowledgeTags } = await import("../use-knowledge");
      renderHook(() => useKnowledgeTags());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/knowledge/tags");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });
  });

  describe("useKnowledgeSearch", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useKnowledgeSearch } = await import("../use-knowledge");
      renderHook(() => useKnowledgeSearch());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/knowledge/search");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useGraphSearch", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useGraphSearch } = await import("../use-knowledge");
      renderHook(() => useGraphSearch());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/knowledge/graph/search");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });
});

// ─── use-renderings.ts ───

describe("use-renderings", () => {
  describe("useRenderingTests", () => {
    it("passes correct key with page params", async () => {
      const { useRenderingTests } = await import("../use-renderings");
      renderHook(() => useRenderingTests({ page: 2, pageSize: 10 }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("/api/v1/rendering/tests");
      expect(key).toContain("page=2");
      expect(key).toContain("page_size=10");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("includes status filter when provided", async () => {
      const { useRenderingTests } = await import("../use-renderings");
      renderHook(() => useRenderingTests({ status: "completed" }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("status=completed");
    });

    it("omits empty params", async () => {
      const { useRenderingTests } = await import("../use-renderings");
      renderHook(() => useRenderingTests({}));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toBe("/api/v1/rendering/tests");
    });
  });

  describe("useRenderingTest", () => {
    it("passes correct key with valid testId", async () => {
      const { useRenderingTest } = await import("../use-renderings");
      renderHook(() => useRenderingTest(5));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/rendering/tests/5");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when testId is null", async () => {
      const { useRenderingTest } = await import("../use-renderings");
      renderHook(() => useRenderingTest(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useRenderingTestPolling", () => {
    it("passes correct key with valid testId", async () => {
      const { useRenderingTestPolling } = await import("../use-renderings");
      renderHook(() => useRenderingTestPolling(3));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/rendering/tests/3");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when testId is null", async () => {
      const { useRenderingTestPolling } = await import("../use-renderings");
      renderHook(() => useRenderingTestPolling(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });

    it("includes refreshInterval option", async () => {
      const { useRenderingTestPolling } = await import("../use-renderings");
      renderHook(() => useRenderingTestPolling(3));
      const options = mockUseSWR.mock.calls[0][2];
      expect(options).toBeDefined();
      expect(options.refreshInterval).toBeDefined();
    });
  });

  describe("useRequestRendering", () => {
    it("uses longMutationFetcher with correct key", async () => {
      const { useRequestRendering } = await import("../use-renderings");
      renderHook(() => useRequestRendering());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/rendering/tests");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(longMutationFetcher);
    });
  });

  describe("useRenderingComparison", () => {
    it("uses longMutationFetcher with correct key", async () => {
      const { useRenderingComparison } = await import("../use-renderings");
      renderHook(() => useRenderingComparison());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/rendering/compare");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(longMutationFetcher);
    });
  });
});

// ─── use-figma.ts (thin wrappers over use-design-sync) ───

describe("use-figma", () => {
  describe("useFigmaDesignTokens", () => {
    it("delegates to design-sync with correct key", async () => {
      const { useFigmaDesignTokens } = await import("../use-figma");
      renderHook(() => useFigmaDesignTokens(8));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/8/tokens");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useFigmaDesignTokens } = await import("../use-figma");
      renderHook(() => useFigmaDesignTokens(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useCreateFigmaConnection", () => {
    it("delegates to design-sync create with correct key", async () => {
      const { useCreateFigmaConnection } = await import("../use-figma");
      renderHook(() => useCreateFigmaConnection());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/connections");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });
});

// ─── use-brand.ts ───

describe("use-brand", () => {
  describe("useBrandConfig", () => {
    it("passes correct key with valid orgId", async () => {
      const { useBrandConfig } = await import("../use-brand");
      renderHook(() => useBrandConfig(5));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/orgs/5/brand");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when orgId is null", async () => {
      const { useBrandConfig } = await import("../use-brand");
      renderHook(() => useBrandConfig(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useUpdateBrandConfig", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useUpdateBrandConfig } = await import("../use-brand");
      renderHook(() => useUpdateBrandConfig());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/orgs/brand");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });
});

// ─── use-design-sync.ts ───

describe("use-design-sync", () => {
  describe("useDesignConnections", () => {
    it("passes correct key", async () => {
      const { useDesignConnections } = await import("../use-design-sync");
      renderHook(() => useDesignConnections());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });
  });

  describe("useDesignConnection", () => {
    it("passes correct key with valid id", async () => {
      const { useDesignConnection } = await import("../use-design-sync");
      renderHook(() => useDesignConnection(3));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/3");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when id is null", async () => {
      const { useDesignConnection } = await import("../use-design-sync");
      renderHook(() => useDesignConnection(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useDesignTokens", () => {
    it("passes correct key with valid connectionId", async () => {
      const { useDesignTokens } = await import("../use-design-sync");
      renderHook(() => useDesignTokens(9));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/9/tokens");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useDesignTokens } = await import("../use-design-sync");
      renderHook(() => useDesignTokens(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useDesignComponents", () => {
    it("passes correct key with valid connectionId", async () => {
      const { useDesignComponents } = await import("../use-design-sync");
      renderHook(() => useDesignComponents(4));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/4/components");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useDesignComponents } = await import("../use-design-sync");
      renderHook(() => useDesignComponents(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useCreateDesignConnection", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useCreateDesignConnection } = await import("../use-design-sync");
      renderHook(() => useCreateDesignConnection());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/connections");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useDeleteDesignConnection", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useDeleteDesignConnection } = await import("../use-design-sync");
      renderHook(() => useDeleteDesignConnection());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/delete");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useSyncDesignConnection", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useSyncDesignConnection } = await import("../use-design-sync");
      renderHook(() => useSyncDesignConnection());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/sync");
      expect(mockUseSWRMutation.mock.calls[0][1]).toEqual(expect.any(Function));
    });
  });

  describe("useDesignFileStructure", () => {
    it("passes correct key with valid connectionId", async () => {
      const { useDesignFileStructure } = await import("../use-design-sync");
      renderHook(() => useDesignFileStructure(6));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/connections/6/file-structure");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("includes depth param when provided", async () => {
      const { useDesignFileStructure } = await import("../use-design-sync");
      renderHook(() => useDesignFileStructure(6, 3));
      expect(mockUseSWR.mock.calls[0][0]).toBe(
        "/api/v1/design-sync/connections/6/file-structure?depth=3",
      );
    });

    it("passes null key when connectionId is null", async () => {
      const { useDesignFileStructure } = await import("../use-design-sync");
      renderHook(() => useDesignFileStructure(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useDesignImport", () => {
    it("passes correct key with valid importId", async () => {
      const { useDesignImport } = await import("../use-design-sync");
      renderHook(() => useDesignImport(11));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/design-sync/imports/11");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when importId is null", async () => {
      const { useDesignImport } = await import("../use-design-sync");
      renderHook(() => useDesignImport(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });

    it("enables polling when flag is true", async () => {
      const { useDesignImport } = await import("../use-design-sync");
      renderHook(() => useDesignImport(11, true));
      const options = mockUseSWR.mock.calls[0][2];
      expect(options.refreshInterval).toBe(2000);
    });
  });

  describe("useDesignImportByTemplate", () => {
    it("passes correct key with valid templateId", async () => {
      const { useDesignImportByTemplate } = await import("../use-design-sync");
      renderHook(() => useDesignImportByTemplate(15, 2));
      expect(mockUseSWR.mock.calls[0][0]).toBe(
        "/api/v1/design-sync/imports/by-template/15?project_id=2",
      );
    });

    it("passes null key when templateId is null", async () => {
      const { useDesignImportByTemplate } = await import("../use-design-sync");
      renderHook(() => useDesignImportByTemplate(null, 2));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useExportImages", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useExportImages } = await import("../use-design-sync");
      renderHook(() => useExportImages());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe(
        "/api/v1/design-sync/connections/export-images",
      );
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useGenerateBrief", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useGenerateBrief } = await import("../use-design-sync");
      renderHook(() => useGenerateBrief());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe(
        "/api/v1/design-sync/connections/generate-brief",
      );
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useCreateDesignImport", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useCreateDesignImport } = await import("../use-design-sync");
      renderHook(() => useCreateDesignImport());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/imports");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useConvertImport", () => {
    it("uses longMutationFetcher with correct key when importId set", async () => {
      const { useConvertImport } = await import("../use-design-sync");
      renderHook(() => useConvertImport(7));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/design-sync/imports/7/convert");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(longMutationFetcher);
    });

    it("passes empty string key when importId is null", async () => {
      const { useConvertImport } = await import("../use-design-sync");
      renderHook(() => useConvertImport(null));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("");
    });
  });

  describe("useExtractComponents", () => {
    it("uses mutation fetcher with correct key when connectionId set", async () => {
      const { useExtractComponents } = await import("../use-design-sync");
      renderHook(() => useExtractComponents(12));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe(
        "/api/v1/design-sync/connections/12/extract-components",
      );
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });

    it("passes empty string key when connectionId is null", async () => {
      const { useExtractComponents } = await import("../use-design-sync");
      renderHook(() => useExtractComponents(null));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("");
    });
  });
});

// ─── use-intelligence-stats.ts ───

describe("use-intelligence-stats", () => {
  describe("useComponentCoverage", () => {
    it("passes correct key", async () => {
      const { useComponentCoverage } = await import("../use-intelligence-stats");
      renderHook(() => useComponentCoverage());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/components/?page=1&page_size=100");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });
  });

  describe("useGraphHealth", () => {
    it("passes graph-health-check as SWR key with custom fetcher", async () => {
      const { useGraphHealth } = await import("../use-intelligence-stats");
      renderHook(() => useGraphHealth());
      expect(mockUseSWR.mock.calls[0][0]).toBe("graph-health-check");
      // Custom inline fetcher, not the shared fetcher
      expect(typeof mockUseSWR.mock.calls[0][1]).toBe("function");
      expect(mockUseSWR.mock.calls[0][1]).not.toBe(fetcher);
    });
  });
});

// ─── use-esp-sync.ts ───

describe("use-esp-sync", () => {
  describe("useESPConnections", () => {
    it("passes correct key", async () => {
      const { useESPConnections } = await import("../use-esp-sync");
      renderHook(() => useESPConnections());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/connectors/sync/connections");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });
  });

  describe("useESPConnection", () => {
    it("passes correct key with valid id", async () => {
      const { useESPConnection } = await import("../use-esp-sync");
      renderHook(() => useESPConnection(4));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/connectors/sync/connections/4");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when id is null", async () => {
      const { useESPConnection } = await import("../use-esp-sync");
      renderHook(() => useESPConnection(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useCreateESPConnection", () => {
    it("uses mutation fetcher with correct key", async () => {
      const { useCreateESPConnection } = await import("../use-esp-sync");
      renderHook(() => useCreateESPConnection());
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/connectors/sync/connections");
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });
  });

  describe("useDeleteESPConnection", () => {
    it("passes correct key with valid id", async () => {
      const { useDeleteESPConnection } = await import("../use-esp-sync");
      renderHook(() => useDeleteESPConnection(6));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/connectors/sync/connections/6");
      // Custom inline fetcher for DELETE
      expect(typeof mockUseSWRMutation.mock.calls[0][1]).toBe("function");
    });

    it("passes empty string key when id is null", async () => {
      const { useDeleteESPConnection } = await import("../use-esp-sync");
      renderHook(() => useDeleteESPConnection(null));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("");
    });
  });

  describe("useESPTemplates", () => {
    it("passes correct key with valid connectionId", async () => {
      const { useESPTemplates } = await import("../use-esp-sync");
      renderHook(() => useESPTemplates(2));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/connectors/sync/connections/2/templates");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useESPTemplates } = await import("../use-esp-sync");
      renderHook(() => useESPTemplates(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useESPTemplate", () => {
    it("passes correct key with both ids", async () => {
      const { useESPTemplate } = await import("../use-esp-sync");
      renderHook(() => useESPTemplate(2, "tpl-abc"));
      expect(mockUseSWR.mock.calls[0][0]).toBe(
        "/api/v1/connectors/sync/connections/2/templates/tpl-abc",
      );
    });

    it("passes null key when connectionId is null", async () => {
      const { useESPTemplate } = await import("../use-esp-sync");
      renderHook(() => useESPTemplate(null, "tpl-abc"));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });

    it("passes null key when templateId is null", async () => {
      const { useESPTemplate } = await import("../use-esp-sync");
      renderHook(() => useESPTemplate(2, null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });
  });

  describe("useImportESPTemplate", () => {
    it("uses mutation fetcher with correct key when connectionId set", async () => {
      const { useImportESPTemplate } = await import("../use-esp-sync");
      renderHook(() => useImportESPTemplate(3));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe(
        "/api/v1/connectors/sync/connections/3/import",
      );
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });

    it("passes empty string key when connectionId is null", async () => {
      const { useImportESPTemplate } = await import("../use-esp-sync");
      renderHook(() => useImportESPTemplate(null));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("");
    });
  });

  describe("usePushToESP", () => {
    it("uses mutation fetcher with correct key when connectionId set", async () => {
      const { usePushToESP } = await import("../use-esp-sync");
      renderHook(() => usePushToESP(5));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe(
        "/api/v1/connectors/sync/connections/5/push",
      );
      expect(mockUseSWRMutation.mock.calls[0][1]).toBe(mutationFetcher);
    });

    it("passes empty string key when connectionId is null", async () => {
      const { usePushToESP } = await import("../use-esp-sync");
      renderHook(() => usePushToESP(null));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("");
    });
  });
});

// ─── use-orgs.ts ───

describe("use-orgs", () => {
  describe("useOrgs", () => {
    it("passes correct key with defaults", async () => {
      const { useOrgs } = await import("../use-orgs");
      renderHook(() => useOrgs());
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("/api/v1/orgs?");
      expect(key).toContain("page=1");
      expect(key).toContain("page_size=50");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes custom page params", async () => {
      const { useOrgs } = await import("../use-orgs");
      renderHook(() => useOrgs({ page: 3, pageSize: 25 }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("page=3");
      expect(key).toContain("page_size=25");
    });
  });
});

// ─── use-update-project.ts ───

describe("use-update-project", () => {
  describe("useUpdateProject", () => {
    it("passes correct key with projectId", async () => {
      const { useUpdateProject } = await import("../use-update-project");
      renderHook(() => useUpdateProject(17));
      expect(mockUseSWRMutation.mock.calls[0][0]).toBe("/api/v1/projects/17");
      // Custom inline fetcher for PATCH
      expect(typeof mockUseSWRMutation.mock.calls[0][1]).toBe("function");
    });
  });
});

// ─── use-email-clients.ts ───

describe("use-email-clients", () => {
  describe("useEmailClients", () => {
    it("passes correct key", async () => {
      const { useEmailClients } = await import("../use-email-clients");
      renderHook(() => useEmailClients());
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/ontology/clients");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("disables revalidateOnFocus", async () => {
      const { useEmailClients } = await import("../use-email-clients");
      renderHook(() => useEmailClients());
      const options = mockUseSWR.mock.calls[0][2];
      expect(options.revalidateOnFocus).toBe(false);
    });
  });
});

// ─── use-compatibility-brief.ts ───

describe("use-compatibility-brief", () => {
  describe("useCompatibilityBrief", () => {
    it("passes correct key with valid projectId", async () => {
      const { useCompatibilityBrief } = await import("../use-compatibility-brief");
      renderHook(() => useCompatibilityBrief(20));
      expect(mockUseSWR.mock.calls[0][0]).toBe("/api/v1/projects/20/compatibility-brief");
      expect(mockUseSWR.mock.calls[0][1]).toBe(fetcher);
    });

    it("passes null key when projectId is null", async () => {
      const { useCompatibilityBrief } = await import("../use-compatibility-brief");
      renderHook(() => useCompatibilityBrief(null));
      expect(mockUseSWR.mock.calls[0][0]).toBeNull();
    });

    it("disables revalidateOnFocus", async () => {
      const { useCompatibilityBrief } = await import("../use-compatibility-brief");
      renderHook(() => useCompatibilityBrief(20));
      const options = mockUseSWR.mock.calls[0][2];
      expect(options.revalidateOnFocus).toBe(false);
    });
  });
});
