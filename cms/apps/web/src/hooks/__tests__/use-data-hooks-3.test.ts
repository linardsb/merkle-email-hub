// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

vi.mock("@/lib/swr-fetcher", () => ({ fetcher: vi.fn() }));
vi.mock("@/lib/mutation-fetcher", () => ({
  mutationFetcher: vi.fn(),
  longMutationFetcher: vi.fn(),
}));
vi.mock("@/lib/auth-fetch", () => ({
  authFetch: vi.fn(),
  LONG_TIMEOUT_MS: 120_000,
}));
vi.mock("@/lib/api-error", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    code?: string;
    constructor(status: number, message: string, code?: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

const mockUseSWR = vi.fn().mockReturnValue({ data: undefined, error: undefined, isLoading: true, mutate: vi.fn() });
const mockUseSWRMutation = vi.fn().mockReturnValue({ trigger: vi.fn(), isMutating: false });
vi.mock("swr", () => ({ default: (...args: unknown[]) => mockUseSWR(...args) }));
vi.mock("swr/mutation", () => ({ default: (...args: unknown[]) => mockUseSWRMutation(...args) }));

import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher, longMutationFetcher } from "@/lib/mutation-fetcher";

beforeEach(() => {
  vi.clearAllMocks();
  mockUseSWR.mockReturnValue({ data: undefined, error: undefined, isLoading: true, mutate: vi.fn() });
  mockUseSWRMutation.mockReturnValue({ trigger: vi.fn(), isMutating: false });
});

// ────────────────────────────────────────────────────────────────────
// 1. use-blueprint-runs
// ────────────────────────────────────────────────────────────────────
describe("use-blueprint-runs", () => {
  describe("useBlueprintRuns", () => {
    it("passes correct SWR key with projectId", async () => {
      const { useBlueprintRuns } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useBlueprintRuns(42));
      expect(mockUseSWR).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/projects/42/blueprint-runs?"),
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false }),
      );
    });

    it("passes null key when projectId is null", async () => {
      const { useBlueprintRuns } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useBlueprintRuns(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });

    it("includes status param when provided", async () => {
      const { useBlueprintRuns } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useBlueprintRuns(1, "completed"));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("status=completed");
    });
  });

  describe("useBlueprintRunDetail", () => {
    it("passes correct key with runId", async () => {
      const { useBlueprintRunDetail } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useBlueprintRunDetail(99));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/blueprint-runs/99", fetcher, expect.any(Object));
    });

    it("passes null key when runId is null", async () => {
      const { useBlueprintRunDetail } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useBlueprintRunDetail(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });
  });

  describe("useRunCheckpoints", () => {
    it("passes correct key with runId", async () => {
      const { useRunCheckpoints } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useRunCheckpoints("abc-123"));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/blueprints/runs/abc-123/checkpoints", fetcher, expect.any(Object));
    });

    it("passes null key when runId is null", async () => {
      const { useRunCheckpoints } = await import("@/hooks/use-blueprint-runs");
      renderHook(() => useRunCheckpoints(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 2. use-blueprint-run (imperative hook — no SWR, uses useState)
// ────────────────────────────────────────────────────────────────────
describe("use-blueprint-run", () => {
  it("returns run, resume, reset, isRunning, result, and error", async () => {
    const { useBlueprintRun } = await import("@/hooks/use-blueprint-run");
    const { result } = renderHook(() => useBlueprintRun({ projectId: 1 }));
    expect(result.current).toHaveProperty("run");
    expect(result.current).toHaveProperty("resume");
    expect(result.current).toHaveProperty("reset");
    expect(result.current.isRunning).toBe(false);
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
  });
});

// ────────────────────────────────────────────────────────────────────
// 3. use-failure-patterns
// ────────────────────────────────────────────────────────────────────
describe("use-failure-patterns", () => {
  describe("useFailurePatterns", () => {
    it("passes correct SWR key with defaults", async () => {
      const { useFailurePatterns } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatterns({}));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("/api/v1/blueprints/failure-patterns?");
      expect(key).toContain("page=1");
      expect(key).toContain("page_size=20");
    });

    it("includes optional filters in key", async () => {
      const { useFailurePatterns } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatterns({ agentName: "scaffolder", projectId: 5 }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("agent_name=scaffolder");
      expect(key).toContain("project_id=5");
    });

    it("passes fetcher", async () => {
      const { useFailurePatterns } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatterns({}));
      expect(mockUseSWR).toHaveBeenCalledWith(expect.any(String), fetcher);
    });
  });

  describe("useFailurePatternStats", () => {
    it("passes correct key", async () => {
      const { useFailurePatternStats } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatternStats());
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("/api/v1/blueprints/failure-patterns/stats");
    });

    it("includes projectId when provided", async () => {
      const { useFailurePatternStats } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatternStats(7));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("project_id=7");
    });

    it("passes fetcher", async () => {
      const { useFailurePatternStats } = await import("@/hooks/use-failure-patterns");
      renderHook(() => useFailurePatternStats());
      expect(mockUseSWR).toHaveBeenCalledWith(expect.any(String), fetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 4. use-agent-skills
// ────────────────────────────────────────────────────────────────────
describe("use-agent-skills", () => {
  describe("useAgentSkills", () => {
    it("passes correct SWR key", async () => {
      const { useAgentSkills } = await import("@/hooks/use-agent-skills");
      renderHook(() => useAgentSkills());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/agents/skills",
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false, dedupingInterval: 600_000 }),
      );
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 5. use-image-gen
// ────────────────────────────────────────────────────────────────────
describe("use-image-gen", () => {
  describe("useProjectImages", () => {
    it("passes correct key with projectId", async () => {
      const { useProjectImages } = await import("@/hooks/use-image-gen");
      renderHook(() => useProjectImages(10));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/projects/10/images", fetcher);
    });

    it("passes null key when projectId is null", async () => {
      const { useProjectImages } = await import("@/hooks/use-image-gen");
      renderHook(() => useProjectImages(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useGenerateImage", () => {
    it("passes correct mutation key and fetcher", async () => {
      const { useGenerateImage } = await import("@/hooks/use-image-gen");
      renderHook(() => useGenerateImage());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/images/generate", mutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 6. use-briefs
// ────────────────────────────────────────────────────────────────────
describe("use-briefs", () => {
  describe("useBriefConnections", () => {
    it("passes correct key", async () => {
      const { useBriefConnections } = await import("@/hooks/use-briefs");
      renderHook(() => useBriefConnections());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/briefs/connections", fetcher);
    });
  });

  describe("useBriefItems", () => {
    it("passes correct key with connectionId", async () => {
      const { useBriefItems } = await import("@/hooks/use-briefs");
      renderHook(() => useBriefItems(3));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/briefs/connections/3/items", fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useBriefItems } = await import("@/hooks/use-briefs");
      renderHook(() => useBriefItems(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useBriefDetail", () => {
    it("passes correct key with itemId", async () => {
      const { useBriefDetail } = await import("@/hooks/use-briefs");
      renderHook(() => useBriefDetail(55));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/briefs/items/55", fetcher);
    });

    it("passes null key when itemId is null", async () => {
      const { useBriefDetail } = await import("@/hooks/use-briefs");
      renderHook(() => useBriefDetail(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useCreateBriefConnection", () => {
    it("passes correct mutation key and fetcher", async () => {
      const { useCreateBriefConnection } = await import("@/hooks/use-briefs");
      renderHook(() => useCreateBriefConnection());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/briefs/connections", mutationFetcher);
    });
  });

  describe("useDeleteBriefConnection", () => {
    it("passes correct mutation key", async () => {
      const { useDeleteBriefConnection } = await import("@/hooks/use-briefs");
      renderHook(() => useDeleteBriefConnection());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/briefs/connections/delete", mutationFetcher);
    });
  });

  describe("useSyncBriefConnection", () => {
    it("passes correct mutation key", async () => {
      const { useSyncBriefConnection } = await import("@/hooks/use-briefs");
      renderHook(() => useSyncBriefConnection());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/briefs/connections/sync", mutationFetcher);
    });
  });

  describe("useImportBrief", () => {
    it("passes correct mutation key", async () => {
      const { useImportBrief } = await import("@/hooks/use-briefs");
      renderHook(() => useImportBrief());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/briefs/import", mutationFetcher);
    });
  });

  describe("useAllBriefItems", () => {
    it("passes base key without options", async () => {
      const { useAllBriefItems } = await import("@/hooks/use-briefs");
      renderHook(() => useAllBriefItems());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/briefs/items", fetcher);
    });

    it("includes query params when options provided", async () => {
      const { useAllBriefItems } = await import("@/hooks/use-briefs");
      renderHook(() => useAllBriefItems({ platform: "jira" as never, status: "new" as never }));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("platform=jira");
      expect(key).toContain("status=new");
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 7. use-outlook-analysis
// ────────────────────────────────────────────────────────────────────
describe("use-outlook-analysis", () => {
  describe("useOutlookAnalysis", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useOutlookAnalysis } = await import("@/hooks/use-outlook-analysis");
      renderHook(() => useOutlookAnalysis());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/outlook-analysis", longMutationFetcher);
    });
  });

  describe("useOutlookModernize", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useOutlookModernize } = await import("@/hooks/use-outlook-analysis");
      renderHook(() => useOutlookModernize());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/outlook-modernize", longMutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 8. use-css-compile
// ────────────────────────────────────────────────────────────────────
describe("use-css-compile", () => {
  describe("useCSSCompile", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useCSSCompile } = await import("@/hooks/use-css-compile");
      renderHook(() => useCSSCompile());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/email/compile-css", longMutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 9. use-gmail-intelligence
// ────────────────────────────────────────────────────────────────────
describe("use-gmail-intelligence", () => {
  describe("useGmailPredict", () => {
    it("passes correct mutation key", async () => {
      const { useGmailPredict } = await import("@/hooks/use-gmail-intelligence");
      renderHook(() => useGmailPredict());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/gmail-predict", longMutationFetcher);
    });
  });

  describe("useGmailOptimize", () => {
    it("passes correct mutation key", async () => {
      const { useGmailOptimize } = await import("@/hooks/use-gmail-intelligence");
      renderHook(() => useGmailOptimize());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/gmail-optimize", longMutationFetcher);
    });
  });

  describe("useDeliverabilityScore", () => {
    it("passes correct mutation key", async () => {
      const { useDeliverabilityScore } = await import("@/hooks/use-gmail-intelligence");
      renderHook(() => useDeliverabilityScore());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/deliverability-score", longMutationFetcher);
    });
  });

  describe("useBIMICheck", () => {
    it("passes correct mutation key", async () => {
      const { useBIMICheck } = await import("@/hooks/use-gmail-intelligence");
      renderHook(() => useBIMICheck());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/bimi-check", longMutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 10. use-schema-inject
// ────────────────────────────────────────────────────────────────────
describe("use-schema-inject", () => {
  describe("useSchemaInject", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useSchemaInject } = await import("@/hooks/use-schema-inject");
      renderHook(() => useSchemaInject());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/email/inject-schema", longMutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 11. use-ontology
// ────────────────────────────────────────────────────────────────────
describe("use-ontology", () => {
  describe("useOntologySyncStatus", () => {
    it("passes correct key with refresh interval", async () => {
      const { useOntologySyncStatus } = await import("@/hooks/use-ontology");
      renderHook(() => useOntologySyncStatus());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/ontology/sync-status",
        fetcher,
        expect.objectContaining({ refreshInterval: 60_000 }),
      );
    });
  });

  describe("useOntologySync", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useOntologySync } = await import("@/hooks/use-ontology");
      renderHook(() => useOntologySync());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/ontology/sync", longMutationFetcher);
    });
  });

  describe("useCompetitiveReport", () => {
    it("passes base key without clientIds", async () => {
      const { useCompetitiveReport } = await import("@/hooks/use-ontology");
      renderHook(() => useCompetitiveReport());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/ontology/competitive-report", fetcher);
    });

    it("includes client_ids params when provided", async () => {
      const { useCompetitiveReport } = await import("@/hooks/use-ontology");
      renderHook(() => useCompetitiveReport(["gmail", "outlook"]));
      const key = mockUseSWR.mock.calls[0][0] as string;
      expect(key).toContain("client_ids=gmail");
      expect(key).toContain("client_ids=outlook");
    });
  });

  describe("useEmailClients", () => {
    it("passes correct key", async () => {
      const { useEmailClients } = await import("@/hooks/use-ontology");
      renderHook(() => useEmailClients());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/ontology/clients", fetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 12. use-mcp
// ────────────────────────────────────────────────────────────────────
describe("use-mcp", () => {
  describe("useMCPStatus", () => {
    it("passes correct key with refresh interval", async () => {
      const { useMCPStatus } = await import("@/hooks/use-mcp");
      renderHook(() => useMCPStatus());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/mcp/status",
        fetcher,
        expect.objectContaining({ refreshInterval: 30_000, revalidateOnFocus: false }),
      );
    });
  });

  describe("useMCPTools", () => {
    it("passes correct key", async () => {
      const { useMCPTools } = await import("@/hooks/use-mcp");
      renderHook(() => useMCPTools());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/mcp/tools",
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false }),
      );
    });
  });

  describe("useMCPConnections", () => {
    it("passes correct key with refresh interval", async () => {
      const { useMCPConnections } = await import("@/hooks/use-mcp");
      renderHook(() => useMCPConnections());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/mcp/connections",
        fetcher,
        expect.objectContaining({ refreshInterval: 15_000 }),
      );
    });
  });

  describe("useToggleMCPTool", () => {
    it("passes correct mutation key", async () => {
      const { useToggleMCPTool } = await import("@/hooks/use-mcp");
      renderHook(() => useToggleMCPTool());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/mcp/tools/toggle", mutationFetcher);
    });
  });

  describe("useMCPApiKeys", () => {
    it("passes correct key", async () => {
      const { useMCPApiKeys } = await import("@/hooks/use-mcp");
      renderHook(() => useMCPApiKeys());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/mcp/api-keys",
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false }),
      );
    });
  });

  describe("useGenerateMCPApiKey", () => {
    it("passes correct mutation key", async () => {
      const { useGenerateMCPApiKey } = await import("@/hooks/use-mcp");
      renderHook(() => useGenerateMCPApiKey());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/mcp/api-keys", mutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 13. use-voice-briefs
// ────────────────────────────────────────────────────────────────────
describe("use-voice-briefs", () => {
  describe("useVoiceBriefs", () => {
    it("passes correct key with projectId", async () => {
      const { useVoiceBriefs } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBriefs(8));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/projects/8/voice-briefs?page=1&page_size=20",
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false, refreshInterval: 30_000 }),
      );
    });

    it("passes null key when projectId is null", async () => {
      const { useVoiceBriefs } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBriefs(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });

    it("includes custom page number", async () => {
      const { useVoiceBriefs } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBriefs(8, 3));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/projects/8/voice-briefs?page=3&page_size=20",
        fetcher,
        expect.any(Object),
      );
    });
  });

  describe("useVoiceBrief", () => {
    it("passes correct key with both params", async () => {
      const { useVoiceBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBrief(5, 12));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/projects/5/voice-briefs/12",
        fetcher,
        expect.objectContaining({ revalidateOnFocus: false }),
      );
    });

    it("passes null key when projectId is null", async () => {
      const { useVoiceBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBrief(null, 12));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });

    it("passes null key when briefId is null", async () => {
      const { useVoiceBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useVoiceBrief(5, null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });
  });

  describe("useGenerateFromBrief", () => {
    it("passes correct mutation key with projectId", async () => {
      const { useGenerateFromBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useGenerateFromBrief(4));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/projects/4/voice-briefs/generate",
        longMutationFetcher,
      );
    });

    it("passes null key when projectId is null", async () => {
      const { useGenerateFromBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useGenerateFromBrief(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(null, longMutationFetcher);
    });
  });

  describe("useDeleteVoiceBrief", () => {
    it("passes correct mutation key with projectId", async () => {
      const { useDeleteVoiceBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useDeleteVoiceBrief(6));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/projects/6/voice-briefs/delete",
        expect.any(Function),
      );
    });

    it("passes null key when projectId is null", async () => {
      const { useDeleteVoiceBrief } = await import("@/hooks/use-voice-briefs");
      renderHook(() => useDeleteVoiceBrief(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(null, expect.any(Function));
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 14. use-visual-qa
// ────────────────────────────────────────────────────────────────────
describe("use-visual-qa", () => {
  describe("useCaptureScreenshots", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useCaptureScreenshots } = await import("@/hooks/use-visual-qa");
      renderHook(() => useCaptureScreenshots());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/rendering/screenshots", longMutationFetcher);
    });
  });

  describe("useVisualDiff", () => {
    it("passes correct mutation key and mutationFetcher", async () => {
      const { useVisualDiff } = await import("@/hooks/use-visual-qa");
      renderHook(() => useVisualDiff());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/rendering/visual-diff", mutationFetcher);
    });
  });

  describe("useBaselines", () => {
    it("passes correct key with entityType and entityId", async () => {
      const { useBaselines } = await import("@/hooks/use-visual-qa");
      renderHook(() => useBaselines("template" as never, 20));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/rendering/baselines/template/20", fetcher);
    });

    it("passes null key when entityType is null", async () => {
      const { useBaselines } = await import("@/hooks/use-visual-qa");
      renderHook(() => useBaselines(null, 20));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });

    it("passes null key when entityId is null", async () => {
      const { useBaselines } = await import("@/hooks/use-visual-qa");
      renderHook(() => useBaselines("template" as never, null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useUpdateBaseline", () => {
    it("passes correct mutation key", async () => {
      const { useUpdateBaseline } = await import("@/hooks/use-visual-qa");
      renderHook(() => useUpdateBaseline("template" as never, 15));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/rendering/baselines/template/15",
        expect.any(Function),
      );
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 15. use-tolgee
// ────────────────────────────────────────────────────────────────────
describe("use-tolgee", () => {
  describe("useTolgeeConnection", () => {
    it("passes correct key with connectionId", async () => {
      const { useTolgeeConnection } = await import("@/hooks/use-tolgee");
      renderHook(() => useTolgeeConnection(9));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/connectors/tolgee/connections/9", fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useTolgeeConnection } = await import("@/hooks/use-tolgee");
      renderHook(() => useTolgeeConnection(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useCreateTolgeeConnection", () => {
    it("passes correct mutation key", async () => {
      const { useCreateTolgeeConnection } = await import("@/hooks/use-tolgee");
      renderHook(() => useCreateTolgeeConnection());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/connectors/tolgee/connect", mutationFetcher);
    });
  });

  describe("useTolgeeLanguages", () => {
    it("passes correct key with connectionId", async () => {
      const { useTolgeeLanguages } = await import("@/hooks/use-tolgee");
      renderHook(() => useTolgeeLanguages(11));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/connectors/tolgee/connections/11/languages", fetcher);
    });

    it("passes null key when connectionId is null", async () => {
      const { useTolgeeLanguages } = await import("@/hooks/use-tolgee");
      renderHook(() => useTolgeeLanguages(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useSyncKeys", () => {
    it("passes correct mutation key", async () => {
      const { useSyncKeys } = await import("@/hooks/use-tolgee");
      renderHook(() => useSyncKeys());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/connectors/tolgee/sync-keys", mutationFetcher);
    });
  });

  describe("usePullTranslations", () => {
    it("passes correct mutation key", async () => {
      const { usePullTranslations } = await import("@/hooks/use-tolgee");
      renderHook(() => usePullTranslations());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/connectors/tolgee/pull", mutationFetcher);
    });
  });

  describe("useLocaleBuild", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useLocaleBuild } = await import("@/hooks/use-tolgee");
      renderHook(() => useLocaleBuild());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/connectors/tolgee/build-locales", longMutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 16. use-plugins
// ────────────────────────────────────────────────────────────────────
describe("use-plugins", () => {
  describe("usePlugins", () => {
    it("passes correct key with refresh interval", async () => {
      const { usePlugins } = await import("@/hooks/use-plugins");
      renderHook(() => usePlugins());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/plugins",
        fetcher,
        expect.objectContaining({ refreshInterval: 60_000 }),
      );
    });
  });

  describe("usePluginHealthSummary", () => {
    it("passes correct key", async () => {
      const { usePluginHealthSummary } = await import("@/hooks/use-plugins");
      renderHook(() => usePluginHealthSummary());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/plugins/health",
        fetcher,
        expect.objectContaining({ refreshInterval: 60_000 }),
      );
    });
  });

  describe("usePluginEnable", () => {
    it("passes correct mutation key with encoded name", async () => {
      const { usePluginEnable } = await import("@/hooks/use-plugins");
      renderHook(() => usePluginEnable("my-plugin"));
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/plugins/my-plugin/enable", mutationFetcher);
    });
  });

  describe("usePluginDisable", () => {
    it("passes correct mutation key", async () => {
      const { usePluginDisable } = await import("@/hooks/use-plugins");
      renderHook(() => usePluginDisable("test"));
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/plugins/test/disable", mutationFetcher);
    });
  });

  describe("usePluginRestart", () => {
    it("passes correct mutation key", async () => {
      const { usePluginRestart } = await import("@/hooks/use-plugins");
      renderHook(() => usePluginRestart("test"));
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/plugins/test/restart", mutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 17. use-workflows
// ────────────────────────────────────────────────────────────────────
describe("use-workflows", () => {
  describe("useWorkflows", () => {
    it("passes correct key with refresh interval", async () => {
      const { useWorkflows } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflows());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/workflows",
        fetcher,
        expect.objectContaining({ refreshInterval: 60_000 }),
      );
    });
  });

  describe("useWorkflowStatus", () => {
    it("passes correct key with executionId", async () => {
      const { useWorkflowStatus } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflowStatus("exec-abc"));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/workflows/exec-abc",
        fetcher,
        expect.objectContaining({ refreshInterval: 30_000 }),
      );
    });

    it("uses faster refresh when isActive", async () => {
      const { useWorkflowStatus } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflowStatus("exec-abc", true));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/workflows/exec-abc",
        fetcher,
        expect.objectContaining({ refreshInterval: 5_000 }),
      );
    });

    it("passes null key when executionId is null", async () => {
      const { useWorkflowStatus } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflowStatus(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher, expect.any(Object));
    });
  });

  describe("useWorkflowLogs", () => {
    it("passes correct key with executionId", async () => {
      const { useWorkflowLogs } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflowLogs("exec-xyz"));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/workflows/exec-xyz/logs", fetcher);
    });

    it("passes null key when executionId is null", async () => {
      const { useWorkflowLogs } = await import("@/hooks/use-workflows");
      renderHook(() => useWorkflowLogs(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, fetcher);
    });
  });

  describe("useTriggerWorkflow", () => {
    it("passes correct mutation key", async () => {
      const { useTriggerWorkflow } = await import("@/hooks/use-workflows");
      renderHook(() => useTriggerWorkflow());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/workflows/trigger", mutationFetcher);
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 18. use-reports
// ────────────────────────────────────────────────────────────────────
describe("use-reports", () => {
  describe("useGenerateQAReport", () => {
    it("passes correct mutation key and longMutationFetcher", async () => {
      const { useGenerateQAReport } = await import("@/hooks/use-reports");
      renderHook(() => useGenerateQAReport());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/reports/qa", longMutationFetcher);
    });
  });

  describe("useGenerateApprovalReport", () => {
    it("passes correct mutation key", async () => {
      const { useGenerateApprovalReport } = await import("@/hooks/use-reports");
      renderHook(() => useGenerateApprovalReport());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/reports/approval", longMutationFetcher);
    });
  });

  describe("useGenerateRegressionReport", () => {
    it("passes correct mutation key", async () => {
      const { useGenerateRegressionReport } = await import("@/hooks/use-reports");
      renderHook(() => useGenerateRegressionReport());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/reports/regression", longMutationFetcher);
    });
  });

  describe("useReportDownload", () => {
    it("passes correct mutation key with reportId", async () => {
      const { useReportDownload } = await import("@/hooks/use-reports");
      renderHook(() => useReportDownload("rpt-123"));
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/reports/rpt-123", expect.any(Function));
    });

    it("passes empty string key when reportId is null", async () => {
      const { useReportDownload } = await import("@/hooks/use-reports");
      renderHook(() => useReportDownload(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith("", expect.any(Function));
    });
  });
});

// ────────────────────────────────────────────────────────────────────
// 19. use-penpot
// ────────────────────────────────────────────────────────────────────
describe("use-penpot", () => {
  describe("usePenpotConnections", () => {
    it("passes correct key with refresh interval", async () => {
      const { usePenpotConnections } = await import("@/hooks/use-penpot");
      renderHook(() => usePenpotConnections());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/design-sync/connections",
        fetcher,
        expect.objectContaining({ refreshInterval: 60_000 }),
      );
    });

    it("filters data to penpot provider only", async () => {
      const { usePenpotConnections } = await import("@/hooks/use-penpot");
      mockUseSWR.mockReturnValue({
        data: [
          { id: 1, provider: "penpot", name: "P1" },
          { id: 2, provider: "figma", name: "F1" },
          { id: 3, provider: "penpot", name: "P2" },
        ],
        error: undefined,
        isLoading: false,
        mutate: vi.fn(),
      });
      const { result } = renderHook(() => usePenpotConnections());
      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.every((c: { provider: string }) => c.provider === "penpot")).toBe(true);
    });
  });
});
