/**
 * Rendering types — re-exported from SDK.
 * Frontend-only types kept locally.
 */
export type {
  ScreenshotResult,
  RenderingTestResponse as RenderingTest,
  RenderingTestRequest,
  RenderingComparisonRequest,
  RenderingDiff,
  RenderingComparisonResponse,
  PaginatedResponseRenderingTestResponse,
} from "@email-hub/sdk";

/** @deprecated Use PaginatedResponseRenderingTestResponse from SDK */
export type PaginatedRenderingTests = {
  items: import("@email-hub/sdk").RenderingTestResponse[];
  total: number;
  page: number;
  page_size: number;
};
