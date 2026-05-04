import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// ── Mock fetcher modules ──
const mockFetcher = vi.fn();
const mockMutationFetcher = vi.fn();
const mockLongMutationFetcher = vi.fn();

vi.mock("@/lib/swr-fetcher", () => ({ fetcher: mockFetcher }));
vi.mock("@/lib/mutation-fetcher", () => ({
  mutationFetcher: mockMutationFetcher,
  longMutationFetcher: mockLongMutationFetcher,
}));
vi.mock("@/lib/auth-fetch", () => ({ authFetch: vi.fn() }));
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

// ── Mock SWR to capture keys ──
const mockUseSWR = vi.fn().mockReturnValue({
  data: undefined,
  error: undefined,
  isLoading: true,
  mutate: vi.fn(),
});
const mockUseSWRMutation = vi.fn().mockReturnValue({
  trigger: vi.fn(),
  isMutating: false,
});

vi.mock("swr", () => ({
  default: (...args: unknown[]) => mockUseSWR(...args),
}));
vi.mock("swr/mutation", () => ({
  default: (...args: unknown[]) => mockUseSWRMutation(...args),
}));

beforeEach(() => {
  mockUseSWR.mockClear();
  mockUseSWRMutation.mockClear();
});

// ═══════════════════════════════════════════════════════════════════
// use-projects
// ═══════════════════════════════════════════════════════════════════
describe("use-projects", () => {
  let useProjects: typeof import("@/hooks/use-projects").useProjects;
  let useProject: typeof import("@/hooks/use-projects").useProject;
  let useCreateProject: typeof import("@/hooks/use-projects").useCreateProject;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-projects");
    useProjects = mod.useProjects;
    useProject = mod.useProject;
    useCreateProject = mod.useCreateProject;
  });

  describe("useProjects", () => {
    it("passes default params key", () => {
      renderHook(() => useProjects());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/projects?page=1&page_size=10", mockFetcher);
    });

    it("passes custom params including clientOrgId and search", () => {
      renderHook(() => useProjects({ page: 2, pageSize: 25, clientOrgId: 5, search: "acme" }));
      const key = mockUseSWR.mock.calls[0]![0] as string;
      expect(key).toContain("page=2");
      expect(key).toContain("page_size=25");
      expect(key).toContain("client_org_id=5");
      expect(key).toContain("search=acme");
    });
  });

  describe("useProject", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useProject(42));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/projects/42", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useProject(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useCreateProject", () => {
    it("passes correct mutation key and fetcher", () => {
      renderHook(() => useCreateProject());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/projects", mockMutationFetcher);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-templates
// ═══════════════════════════════════════════════════════════════════
describe("use-templates", () => {
  let useTemplates: typeof import("@/hooks/use-templates").useTemplates;
  let useTemplate: typeof import("@/hooks/use-templates").useTemplate;
  let useTemplateVersions: typeof import("@/hooks/use-templates").useTemplateVersions;
  let useTemplateVersion: typeof import("@/hooks/use-templates").useTemplateVersion;
  let useCreateTemplate: typeof import("@/hooks/use-templates").useCreateTemplate;
  let useSaveVersion: typeof import("@/hooks/use-templates").useSaveVersion;
  let useUpdateTemplate: typeof import("@/hooks/use-templates").useUpdateTemplate;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-templates");
    useTemplates = mod.useTemplates;
    useTemplate = mod.useTemplate;
    useTemplateVersions = mod.useTemplateVersions;
    useTemplateVersion = mod.useTemplateVersion;
    useCreateTemplate = mod.useCreateTemplate;
    useSaveVersion = mod.useSaveVersion;
    useUpdateTemplate = mod.useUpdateTemplate;
  });

  describe("useTemplates", () => {
    it("passes correct key with default params", () => {
      renderHook(() => useTemplates(1));
      const key = mockUseSWR.mock.calls[0]![0] as string;
      expect(key).toBe("/api/v1/projects/1/templates?page=1&page_size=50");
    });

    it("passes null key when projectId is null", () => {
      renderHook(() => useTemplates(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });

    it("includes search and status in key", () => {
      renderHook(() =>
        useTemplates(3, { page: 2, pageSize: 10, search: "promo", status: "draft" }),
      );
      const key = mockUseSWR.mock.calls[0]![0] as string;
      expect(key).toContain("page=2");
      expect(key).toContain("page_size=10");
      expect(key).toContain("search=promo");
      expect(key).toContain("status=draft");
    });
  });

  describe("useTemplate", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useTemplate(7));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/templates/7", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useTemplate(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useTemplateVersions", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useTemplateVersions(5));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/templates/5/versions", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useTemplateVersions(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useTemplateVersion", () => {
    it("passes correct key when both params present", () => {
      renderHook(() => useTemplateVersion(5, 2));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/templates/5/versions/2", mockFetcher);
    });

    it("passes null key when templateId is null", () => {
      renderHook(() => useTemplateVersion(null, 2));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });

    it("passes null key when versionNumber is null", () => {
      renderHook(() => useTemplateVersion(5, null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useCreateTemplate", () => {
    it("passes correct mutation key for valid projectId", () => {
      renderHook(() => useCreateTemplate(3));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/projects/3/templates",
        mockMutationFetcher,
      );
    });

    it("passes null key when projectId is null", () => {
      renderHook(() => useCreateTemplate(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(null, mockMutationFetcher);
    });
  });

  describe("useSaveVersion", () => {
    it("passes correct mutation key for valid templateId", () => {
      renderHook(() => useSaveVersion(9));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/templates/9/versions",
        mockMutationFetcher,
      );
    });

    it("passes null key when templateId is null", () => {
      renderHook(() => useSaveVersion(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(null, mockMutationFetcher);
    });
  });

  describe("useUpdateTemplate", () => {
    it("passes correct mutation key for valid templateId", () => {
      renderHook(() => useUpdateTemplate(4));
      const key = mockUseSWRMutation.mock.calls[0]![0];
      expect(key).toBe("/api/v1/templates/4");
    });

    it("passes null key when templateId is null", () => {
      renderHook(() => useUpdateTemplate(null));
      const key = mockUseSWRMutation.mock.calls[0]![0];
      expect(key).toBeNull();
    });

    it("uses patchFetcher (not mutationFetcher)", () => {
      renderHook(() => useUpdateTemplate(4));
      const fetcherArg = mockUseSWRMutation.mock.calls[0]![1];
      expect(fetcherArg).not.toBe(mockMutationFetcher);
      expect(fetcherArg).not.toBe(mockLongMutationFetcher);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-qa
// ═══════════════════════════════════════════════════════════════════
describe("use-qa", () => {
  let useQARun: typeof import("@/hooks/use-qa").useQARun;
  let useQAResult: typeof import("@/hooks/use-qa").useQAResult;
  let useQALatest: typeof import("@/hooks/use-qa").useQALatest;
  let useQAResults: typeof import("@/hooks/use-qa").useQAResults;
  let useQAOverride: typeof import("@/hooks/use-qa").useQAOverride;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-qa");
    useQARun = mod.useQARun;
    useQAResult = mod.useQAResult;
    useQALatest = mod.useQALatest;
    useQAResults = mod.useQAResults;
    useQAOverride = mod.useQAOverride;
  });

  describe("useQARun", () => {
    it("uses longMutationFetcher for QA run", () => {
      renderHook(() => useQARun());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/qa/run", mockLongMutationFetcher);
    });
  });

  describe("useQAResult", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useQAResult(10));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/qa/results/10", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useQAResult(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useQALatest", () => {
    it("passes correct key for valid templateVersionId", () => {
      renderHook(() => useQALatest(77));
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/qa/results/latest?template_version_id=77",
        mockFetcher,
      );
    });

    it("passes null key when templateVersionId is null", () => {
      renderHook(() => useQALatest(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useQAResults", () => {
    it("passes default params key", () => {
      renderHook(() => useQAResults());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/qa/results?page=1&page_size=20",
        mockFetcher,
      );
    });

    it("includes optional filters in key", () => {
      renderHook(() => useQAResults({ page: 3, pageSize: 5, templateVersionId: 12, passed: true }));
      const key = mockUseSWR.mock.calls[0]![0] as string;
      expect(key).toContain("page=3");
      expect(key).toContain("page_size=5");
      expect(key).toContain("template_version_id=12");
      expect(key).toContain("passed=true");
    });
  });

  describe("useQAOverride", () => {
    it("passes correct mutation key for valid resultId", () => {
      renderHook(() => useQAOverride(8));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/qa/results/8/override",
        mockMutationFetcher,
      );
    });

    it("passes null key when resultId is null", () => {
      renderHook(() => useQAOverride(null));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(null, mockMutationFetcher);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-approvals
// ═══════════════════════════════════════════════════════════════════
describe("use-approvals", () => {
  let useApprovals: typeof import("@/hooks/use-approvals").useApprovals;
  let useApproval: typeof import("@/hooks/use-approvals").useApproval;
  let useCreateApproval: typeof import("@/hooks/use-approvals").useCreateApproval;
  let useApprovalDecide: typeof import("@/hooks/use-approvals").useApprovalDecide;
  let useApprovalFeedback: typeof import("@/hooks/use-approvals").useApprovalFeedback;
  let useAddFeedback: typeof import("@/hooks/use-approvals").useAddFeedback;
  let useApprovalAudit: typeof import("@/hooks/use-approvals").useApprovalAudit;
  let useBuild: typeof import("@/hooks/use-approvals").useBuild;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-approvals");
    useApprovals = mod.useApprovals;
    useApproval = mod.useApproval;
    useCreateApproval = mod.useCreateApproval;
    useApprovalDecide = mod.useApprovalDecide;
    useApprovalFeedback = mod.useApprovalFeedback;
    useAddFeedback = mod.useAddFeedback;
    useApprovalAudit = mod.useApprovalAudit;
    useBuild = mod.useBuild;
  });

  describe("useApprovals", () => {
    it("passes correct key for valid projectId", () => {
      renderHook(() => useApprovals(5));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/approvals/?project_id=5", mockFetcher);
    });

    it("passes null key when projectId is null", () => {
      renderHook(() => useApprovals(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useApproval", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useApproval(11));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/approvals/11", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useApproval(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useCreateApproval", () => {
    it("passes correct mutation key and fetcher", () => {
      renderHook(() => useCreateApproval());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/approvals/", mockMutationFetcher);
    });
  });

  describe("useApprovalDecide", () => {
    it("passes correct mutation key", () => {
      renderHook(() => useApprovalDecide(15));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/approvals/15/decide",
        mockMutationFetcher,
      );
    });
  });

  describe("useApprovalFeedback", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useApprovalFeedback(20));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/approvals/20/feedback", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useApprovalFeedback(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useAddFeedback", () => {
    it("passes correct mutation key", () => {
      renderHook(() => useAddFeedback(22));
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/approvals/22/feedback",
        mockMutationFetcher,
      );
    });
  });

  describe("useApprovalAudit", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useApprovalAudit(30));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/approvals/30/audit", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useApprovalAudit(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useBuild", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useBuild(99));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/email/builds/99", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useBuild(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-components
// ═══════════════════════════════════════════════════════════════════
describe("use-components", () => {
  let useComponents: typeof import("@/hooks/use-components").useComponents;
  let useComponent: typeof import("@/hooks/use-components").useComponent;
  let useComponentVersions: typeof import("@/hooks/use-components").useComponentVersions;
  let useComponentCompatibility: typeof import("@/hooks/use-components").useComponentCompatibility;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-components");
    useComponents = mod.useComponents;
    useComponent = mod.useComponent;
    useComponentVersions = mod.useComponentVersions;
    useComponentCompatibility = mod.useComponentCompatibility;
  });

  describe("useComponents", () => {
    it("passes default params key", () => {
      renderHook(() => useComponents());
      expect(mockUseSWR).toHaveBeenCalledWith(
        "/api/v1/components/?page=1&page_size=20",
        mockFetcher,
      );
    });

    it("includes category and search in key", () => {
      renderHook(() => useComponents({ page: 2, pageSize: 10, category: "header", search: "nav" }));
      const key = mockUseSWR.mock.calls[0]![0] as string;
      expect(key).toContain("page=2");
      expect(key).toContain("page_size=10");
      expect(key).toContain("category=header");
      expect(key).toContain("search=nav");
    });
  });

  describe("useComponent", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useComponent(6));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/components/6", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useComponent(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useComponentVersions", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useComponentVersions(6));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/components/6/versions", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useComponentVersions(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useComponentCompatibility", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => useComponentCompatibility(6));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/components/6/compatibility", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => useComponentCompatibility(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-connectors
// ═══════════════════════════════════════════════════════════════════
describe("use-connectors", () => {
  let useExport: typeof import("@/hooks/use-connectors").useExport;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-connectors");
    useExport = mod.useExport;
  });

  describe("useExport", () => {
    it("uses longMutationFetcher for export", () => {
      renderHook(() => useExport());
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/connectors/export",
        mockLongMutationFetcher,
      );
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-email
// ═══════════════════════════════════════════════════════════════════
describe("use-email", () => {
  let useEmailBuild: typeof import("@/hooks/use-email").useEmailBuild;
  let useEmailPreview: typeof import("@/hooks/use-email").useEmailPreview;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-email");
    useEmailBuild = mod.useEmailBuild;
    useEmailPreview = mod.useEmailPreview;
  });

  describe("useEmailBuild", () => {
    it("uses longMutationFetcher for email build", () => {
      renderHook(() => useEmailBuild());
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/email/build",
        mockLongMutationFetcher,
        { throwOnError: false },
      );
    });
  });

  describe("useEmailPreview", () => {
    it("uses longMutationFetcher for email preview", () => {
      renderHook(() => useEmailPreview());
      expect(mockUseSWRMutation).toHaveBeenCalledWith(
        "/api/v1/email/preview",
        mockLongMutationFetcher,
        { throwOnError: false },
      );
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// use-personas
// ═══════════════════════════════════════════════════════════════════
describe("use-personas", () => {
  let usePersonas: typeof import("@/hooks/use-personas").usePersonas;
  let usePersona: typeof import("@/hooks/use-personas").usePersona;
  let useCreatePersona: typeof import("@/hooks/use-personas").useCreatePersona;

  beforeEach(async () => {
    const mod = await import("@/hooks/use-personas");
    usePersonas = mod.usePersonas;
    usePersona = mod.usePersona;
    useCreatePersona = mod.useCreatePersona;
  });

  describe("usePersonas", () => {
    it("passes correct key", () => {
      renderHook(() => usePersonas());
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/personas", mockFetcher);
    });
  });

  describe("usePersona", () => {
    it("passes correct key for valid id", () => {
      renderHook(() => usePersona(3));
      expect(mockUseSWR).toHaveBeenCalledWith("/api/v1/personas/3", mockFetcher);
    });

    it("passes null key when id is null", () => {
      renderHook(() => usePersona(null));
      expect(mockUseSWR).toHaveBeenCalledWith(null, mockFetcher);
    });
  });

  describe("useCreatePersona", () => {
    it("passes correct mutation key and fetcher", () => {
      renderHook(() => useCreatePersona());
      expect(mockUseSWRMutation).toHaveBeenCalledWith("/api/v1/personas", mockMutationFetcher);
    });
  });
});
