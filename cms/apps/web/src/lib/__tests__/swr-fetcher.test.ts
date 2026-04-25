import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock authFetch ──
const mockAuthFetch = vi.fn();
vi.mock("@/lib/auth-fetch", () => ({
  authFetch: (...args: unknown[]) => mockAuthFetch(...args),
}));

// Import after mock setup
const { fetcher } = await import("../swr-fetcher");

/** Helper to create a minimal Response-like object. */
function makeResponse(status: number, body?: Record<string, unknown>): Response {
  const ok = status >= 200 && status < 300;
  return {
    status,
    ok,
    statusText: ok ? "OK" : status === 304 ? "Not Modified" : "Error",
    headers: new Headers(),
    json:
      body !== undefined
        ? vi.fn().mockResolvedValue(body)
        : vi.fn().mockRejectedValue(new SyntaxError("Unexpected end of JSON input")),
  } as unknown as Response;
}

beforeEach(() => {
  mockAuthFetch.mockReset();
});

describe("fetcher", () => {
  it("returns parsed JSON on 200", async () => {
    const data = { id: 1, name: "test" };
    mockAuthFetch.mockResolvedValue(makeResponse(200, data));

    const result = await fetcher("/api/v1/items");

    expect(result).toEqual(data);
    expect(mockAuthFetch).toHaveBeenCalledWith("/api/v1/items");
  });

  it("returns undefined on 304 Not Modified (SSR path)", async () => {
    mockAuthFetch.mockResolvedValue(makeResponse(304));

    const result = await fetcher("/api/v1/items");

    expect(result).toBeUndefined();
  });

  it("does not call res.json() on 304", async () => {
    const res = makeResponse(304);
    mockAuthFetch.mockResolvedValue(res);

    await fetcher("/api/v1/items");

    expect(res.json).not.toHaveBeenCalled();
  });

  it("throws ApiError on non-ok response", async () => {
    const errorBody = { error: "Not found", type: "NOT_FOUND" };
    mockAuthFetch.mockResolvedValue(makeResponse(404, errorBody));

    await expect(fetcher("/api/v1/items")).rejects.toThrow("Not found");
    // Verify a second call for property assertions
    mockAuthFetch.mockResolvedValue(makeResponse(404, errorBody));
    try {
      await fetcher("/api/v1/items");
      expect.unreachable("should have thrown");
    } catch (err: unknown) {
      const error = err as { status: number; code: string };
      expect(error.status).toBe(404);
      expect(error.code).toBe("NOT_FOUND");
    }
  });

  it("falls back to statusText when error body is unparseable", async () => {
    const res = {
      status: 500,
      ok: false,
      statusText: "Internal Server Error",
      headers: new Headers(),
      json: vi.fn().mockRejectedValue(new SyntaxError("bad json")),
    } as unknown as Response;
    mockAuthFetch.mockResolvedValue(res);

    await expect(fetcher("/api/v1/items")).rejects.toMatchObject({
      status: 500,
      message: "Internal Server Error",
    });
  });
});
