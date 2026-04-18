import { clearSession, getSession, setSessionFromAuth } from "@/lib/auth/session";
import type { AuthResponse } from "@/lib/api/types";
import { env } from "@/lib/env";

const API_BASE_URL = env.API_BASE_URL;

interface ApiRequestOptions {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
}

async function refreshAccessToken(): Promise<string | null> {
  const session = getSession();
  if (!session?.refreshToken) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
      cache: "no-store",
    });

    if (!response.ok) {
      clearSession();
      return null;
    }

    const refreshed = (await response.json()) as AuthResponse;
    const nextSession = setSessionFromAuth(refreshed);
    return nextSession.accessToken;
  } catch {
    clearSession();
    return null;
  }
}

async function executeRequest(path: string, init?: RequestInit, options?: ApiRequestOptions): Promise<Response> {
  const authEnabled = options?.auth ?? true;
  const shouldRetry = options?.retryOnUnauthorized ?? true;

  const headers = new Headers(init?.headers ?? {});
  if (authEnabled) {
    const session = getSession();
    if (session?.accessToken) {
      headers.set("Authorization", `Bearer ${session.accessToken}`);
    }
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (response.status === 401 && authEnabled && shouldRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        headers,
        cache: "no-store",
      });
    }
  }

  return response;
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  options?: ApiRequestOptions,
): Promise<T> {
  const response = await executeRequest(path, init, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API error: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiBinaryRequest(
  path: string,
  init?: RequestInit,
  options?: ApiRequestOptions,
): Promise<Blob> {
  const response = await executeRequest(path, init, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API error: ${response.status}`);
  }
  return response.blob();
}

export { API_BASE_URL };
