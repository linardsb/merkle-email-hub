import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useWorkspaceDialogs } from "../use-workspace-dialogs";

describe("useWorkspaceDialogs", () => {
  it("starts with every dialog closed", () => {
    const { result } = renderHook(() => useWorkspaceDialogs());
    expect(result.current.exportOpen).toBe(false);
    expect(result.current.imageGenOpen).toBe(false);
    expect(result.current.briefOpen).toBe(false);
    expect(result.current.blueprintOpen).toBe(false);
    expect(result.current.pushOpen).toBe(false);
    expect(result.current.approvalOpen).toBe(false);
  });

  it("toggles each dialog independently", () => {
    const { result } = renderHook(() => useWorkspaceDialogs());

    act(() => result.current.setExportOpen(true));
    expect(result.current.exportOpen).toBe(true);
    expect(result.current.pushOpen).toBe(false);

    act(() => result.current.setPushOpen(true));
    expect(result.current.exportOpen).toBe(true);
    expect(result.current.pushOpen).toBe(true);

    act(() => result.current.setExportOpen(false));
    expect(result.current.exportOpen).toBe(false);
    expect(result.current.pushOpen).toBe(true);
  });
});
