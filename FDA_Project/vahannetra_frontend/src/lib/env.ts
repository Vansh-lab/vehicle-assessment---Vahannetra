type OptionalString = string | undefined;

function readEnv(viteKey: string, legacyKey: string, fallback?: string): OptionalString {
  const viteValue =
    typeof import.meta !== "undefined"
      ? (import.meta.env as Record<string, string | undefined>)[viteKey]
      : undefined;
  const legacyValue =
    typeof process !== "undefined"
      ? (process.env as Record<string, string | undefined> | undefined)?.[legacyKey]
      : undefined;
  return viteValue ?? legacyValue ?? fallback;
}

function readBool(viteKey: string, legacyKey: string, fallback = false): boolean {
  return readEnv(viteKey, legacyKey, String(fallback)) === "true";
}

export const env = {
  API_BASE_URL: readEnv("VITE_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000")!,
  USE_BACKEND: readBool("VITE_USE_BACKEND", "NEXT_PUBLIC_USE_BACKEND", false),
  E2E_BYPASS_AUTH: readBool("VITE_E2E_BYPASS_AUTH", "NEXT_PUBLIC_E2E_BYPASS_AUTH", false),
  E2E_BYPASS_CONFIRM: readBool("VITE_E2E_BYPASS_CONFIRM", "NEXT_PUBLIC_E2E_BYPASS_CONFIRM", false),
  IS_PRODUCTION:
    (typeof import.meta !== "undefined" ? import.meta.env.PROD : undefined) ??
    readEnv("NODE_ENV", "NODE_ENV", "development") === "production",
};
