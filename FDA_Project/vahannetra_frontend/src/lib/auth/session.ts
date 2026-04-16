import type { AuthResponse } from "@/lib/api/types";

const SESSION_KEY = "vahannetra_session";

export interface SessionState {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  user: AuthResponse["user"];
  organization: AuthResponse["organization"];
}

export function getSession(): SessionState | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as SessionState;
    if (!parsed.accessToken || !parsed.refreshToken) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function setSessionFromAuth(auth: AuthResponse): SessionState {
  const issuedAt = new Date(auth.issued_at).getTime();
  const session: SessionState = {
    accessToken: auth.access_token,
    refreshToken: auth.refresh_token,
    expiresAt: issuedAt + auth.expires_in * 1000,
    user: auth.user,
    organization: auth.organization,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  return session;
}

export function clearSession(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(SESSION_KEY);
  }
}

export function isSessionActive(): boolean {
  const session = getSession();
  if (!session) return false;
  return session.expiresAt > Date.now();
}
