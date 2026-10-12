import { FALLBACK_CANDIDATES } from "./fallback";
import { Candidate, CandidateResponse } from "./types";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`API error ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getCandidates(): Promise<CandidateResponse> {
  try {
    return await request<CandidateResponse>("/api/candidates?limit=100");
  } catch {
    return {
      items: FALLBACK_CANDIDATES,
      count: FALLBACK_CANDIDATES.length,
      source: "demo fallback",
      modified: null,
      advisory: FALLBACK_CANDIDATES[0].advisory
    };
  }
}

export async function getNearby(
  latitude: number,
  longitude: number
): Promise<Candidate[]> {
  try {
    const result = await request<{ items: Candidate[] }>(
      `/api/nearby?latitude=${latitude}&longitude=${longitude}&radius_m=50000&limit=20`
    );
    return result.items;
  } catch {
    return FALLBACK_CANDIDATES;
  }
}

export async function saveFieldNote(
  candidateId: string,
  note: string,
  photoUri?: string,
  latitude?: number,
  longitude?: number
): Promise<void> {
  await request("/api/field-notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_id: candidateId,
      note,
      photo_uri: photoUri,
      latitude,
      longitude
    })
  });
}

export function isApiConfigured(): boolean {
  return Boolean(process.env.EXPO_PUBLIC_API_URL);
}
