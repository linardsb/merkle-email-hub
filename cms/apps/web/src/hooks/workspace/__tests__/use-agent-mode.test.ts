import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

const searchParamsMock = { get: vi.fn() };

vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParamsMock,
}));

import { useAgentMode } from "../use-agent-mode";

describe("useAgentMode", () => {
  beforeEach(() => {
    searchParamsMock.get.mockReset();
  });

  it("returns undefined when no agent param is present", () => {
    searchParamsMock.get.mockReturnValue(null);
    const { result } = renderHook(() => useAgentMode());
    expect(result.current).toBeUndefined();
  });

  it("returns the agent when the param is a valid AgentMode", () => {
    searchParamsMock.get.mockReturnValue("scaffolder");
    const { result } = renderHook(() => useAgentMode());
    expect(result.current).toBe("scaffolder");
  });

  it("returns undefined when the param is not a known agent", () => {
    searchParamsMock.get.mockReturnValue("not-a-real-agent");
    const { result } = renderHook(() => useAgentMode());
    expect(result.current).toBeUndefined();
  });
});
