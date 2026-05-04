import type { BuilderSection } from "@/types/visual-builder";
import { DEFAULT_RESPONSIVE, DEFAULT_ADVANCED } from "@/types/visual-builder";

export function createSectionDefaults(): Pick<
  BuilderSection,
  "slotDefinitions" | "defaultTokens" | "responsive" | "advanced"
> {
  return {
    slotDefinitions: [],
    defaultTokens: null,
    responsive: { ...DEFAULT_RESPONSIVE },
    advanced: { ...DEFAULT_ADVANCED },
  };
}
