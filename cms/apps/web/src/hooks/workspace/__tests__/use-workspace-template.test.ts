import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import type { TemplateResponse } from "@/types/templates";

const searchParamsMock = { get: vi.fn() };

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParamsMock,
}));

vi.mock("@/hooks/use-projects", () => ({
  useProject: () => ({ data: { id: 1, name: "P" }, isLoading: false, error: null }),
}));

const useTemplatesMock = vi.fn();
const useTemplateVersionMock = vi.fn();
vi.mock("@/hooks/use-templates", () => ({
  useTemplates: (...args: unknown[]) => useTemplatesMock(...args),
  useTemplateVersion: (...args: unknown[]) => useTemplateVersionMock(...args),
  useSaveVersion: () => ({ trigger: vi.fn(), isMutating: false }),
  useCreateTemplate: () => ({ trigger: vi.fn() }),
}));

import { useWorkspaceTemplate } from "../use-workspace-template";

function makeTemplate(id: number, latestVersion = 1): TemplateResponse {
  return {
    id,
    project_id: 1,
    name: `T${id}`,
    html_source: "",
    latest_version: latestVersion,
    created_at: "",
    updated_at: "",
  } as unknown as TemplateResponse;
}

describe("useWorkspaceTemplate", () => {
  beforeEach(() => {
    searchParamsMock.get.mockReset();
    useTemplatesMock.mockReset();
    useTemplateVersionMock.mockReset();
    useTemplateVersionMock.mockReturnValue({ data: null });
  });

  it("auto-selects the first template when none is in the URL", () => {
    searchParamsMock.get.mockReturnValue(null);
    useTemplatesMock.mockReturnValue({
      data: { items: [makeTemplate(11), makeTemplate(22)] },
      isLoading: false,
      mutate: vi.fn(),
    });

    const { result, rerender } = renderHook(() => useWorkspaceTemplate(1));
    rerender();
    expect(result.current.activeTemplateId).toBe(11);
    expect(result.current.activeTemplate?.id).toBe(11);
  });

  it("seeds activeTemplateId from the URL parameter", () => {
    searchParamsMock.get.mockReturnValue("22");
    useTemplatesMock.mockReturnValue({
      data: { items: [makeTemplate(11), makeTemplate(22)] },
      isLoading: false,
      mutate: vi.fn(),
    });

    const { result } = renderHook(() => useWorkspaceTemplate(1));
    expect(result.current.activeTemplateId).toBe(22);
  });
});
