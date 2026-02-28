"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/swr-fetcher";
import type { PersonaResponse } from "@merkle-email-hub/sdk";

export function usePersonas() {
  return useSWR<PersonaResponse[]>("/api/v1/personas", fetcher);
}

export function usePersona(personaId: number | null) {
  return useSWR<PersonaResponse>(
    personaId ? `/api/v1/personas/${personaId}` : null,
    fetcher
  );
}
