"use client";

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { fetcher } from "@/lib/swr-fetcher";
import { mutationFetcher } from "@/lib/mutation-fetcher";
import type { PersonaCreate, PersonaResponse } from "@email-hub/sdk";

export function usePersonas() {
  return useSWR<PersonaResponse[]>("/api/v1/personas", fetcher);
}

export function usePersona(personaId: number | null) {
  return useSWR<PersonaResponse>(personaId ? `/api/v1/personas/${personaId}` : null, fetcher);
}

export function useCreatePersona() {
  return useSWRMutation<PersonaResponse, Error, string, PersonaCreate>(
    "/api/v1/personas",
    mutationFetcher,
  );
}
