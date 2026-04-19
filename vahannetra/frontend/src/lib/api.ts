import { env } from "./env";
import type { AnalyzeAccepted, AnalyzeInput, AnalyzeUrlInput, JobResult } from "../types/assessment";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function analyze(payload: AnalyzeInput): Promise<AnalyzeAccepted> {
  return jsonFetch<AnalyzeAccepted>("/api/v1/analyze", {
    method: "POST",
    body: JSON.stringify({
      media_type: payload.media_type ?? "image",
      source_count: payload.source_count ?? 1,
    }),
  });
}

export function analyzeUrl(payload: AnalyzeUrlInput): Promise<AnalyzeAccepted> {
  return jsonFetch<AnalyzeAccepted>("/api/v1/analyze/url", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getResult(jobId: string): Promise<JobResult> {
  return jsonFetch<JobResult>(`/api/v1/results/${jobId}`);
}
