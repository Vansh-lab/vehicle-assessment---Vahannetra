type OptionalString = string | undefined;

function readNextPublicEnv(key: string): OptionalString {
  switch (key) {
    case "NEXT_PUBLIC_API_BASE_URL":
      return process.env.NEXT_PUBLIC_API_BASE_URL;
    case "NEXT_PUBLIC_USE_BACKEND":
      return process.env.NEXT_PUBLIC_USE_BACKEND;
    case "NODE_ENV":
      return process.env.NODE_ENV;
    default:
      return undefined;
  }
}

function readEnv(viteKey: string, legacyKey: string, fallback?: string): OptionalString {
  const viteEnv =
    typeof import.meta !== "undefined"
      ? (import.meta as { env?: Record<string, string | undefined> }).env
      : undefined;
  const viteValue = viteEnv?.[viteKey];
  const legacyValue = typeof process !== "undefined" ? readNextPublicEnv(legacyKey) : undefined;
  return viteValue ?? legacyValue ?? fallback;
}

function readBool(viteKey: string, legacyKey: string, fallback = false): boolean {
  const rawValue = readEnv(viteKey, legacyKey);
  if (rawValue === undefined) {
    return fallback;
  }
  return rawValue.trim().toLowerCase() === "true";
}

function requireEnv(value: OptionalString, envKey: string): string {
  if (!value || value.trim().length === 0) {
    throw new Error(`Missing required environment variable: ${envKey}`);
  }
  return value;
}

export const env = {
  API_BASE_URL: requireEnv(
    readEnv("VITE_API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000"),
    "VITE_API_BASE_URL"
  ),
  USE_BACKEND: readBool("VITE_USE_BACKEND", "NEXT_PUBLIC_USE_BACKEND", true),
};
