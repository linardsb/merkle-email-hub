import { describe, it, expect } from "vitest";
import { POLL, DEDUP, SWR_PRESETS } from "../swr-constants";

describe("swr-constants", () => {
  describe("POLL", () => {
    it("defines all interval tiers with expected values", () => {
      expect(POLL.off).toBe(0);
      expect(POLL.realtime).toBe(3_000);
      expect(POLL.frequent).toBe(5_000);
      expect(POLL.moderate).toBe(15_000);
      expect(POLL.status).toBe(30_000);
      expect(POLL.background).toBe(60_000);
    });

    it("maintains ascending order invariant", () => {
      const values = [
        POLL.off,
        POLL.realtime,
        POLL.frequent,
        POLL.moderate,
        POLL.status,
        POLL.background,
      ];
      for (let i = 1; i < values.length; i++) {
        expect(values[i]).toBeGreaterThan(values[i - 1]!);
      }
    });
  });

  describe("DEDUP", () => {
    it("defines all deduplication tiers", () => {
      expect(DEDUP.standard).toBe(5_000);
      expect(DEDUP.reference).toBe(300_000);
      expect(DEDUP.static).toBe(600_000);
    });
  });

  describe("SWR_PRESETS", () => {
    it("polling preset disables focus revalidation", () => {
      expect(SWR_PRESETS.polling.revalidateOnFocus).toBe(false);
      expect(SWR_PRESETS.polling.dedupingInterval).toBe(DEDUP.standard);
    });

    it("static preset disables focus and reconnect revalidation", () => {
      expect(SWR_PRESETS.static.revalidateOnFocus).toBe(false);
      expect(SWR_PRESETS.static.revalidateOnReconnect).toBe(false);
      expect(SWR_PRESETS.static.dedupingInterval).toBe(DEDUP.static);
    });

    it("reference preset uses reference dedup", () => {
      expect(SWR_PRESETS.reference.dedupingInterval).toBe(DEDUP.reference);
      expect(SWR_PRESETS.reference.revalidateOnFocus).toBe(false);
    });

    it("interactive preset enables focus revalidation", () => {
      expect(SWR_PRESETS.interactive.revalidateOnFocus).toBe(true);
      expect(SWR_PRESETS.interactive.dedupingInterval).toBe(DEDUP.standard);
    });
  });
});
