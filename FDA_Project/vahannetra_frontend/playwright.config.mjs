import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "on-first-retry",
  },
  webServer: {
    command:
      "VITE_USE_BACKEND=false VITE_E2E_BYPASS_AUTH=true VITE_E2E_BYPASS_CONFIRM=true NEXT_PUBLIC_USE_BACKEND=false NEXT_PUBLIC_E2E_BYPASS_AUTH=true NEXT_PUBLIC_E2E_BYPASS_CONFIRM=true npm run dev -- --hostname 127.0.0.1 --port 3001",
    url: "http://127.0.0.1:3001/login",
    timeout: 120000,
    reuseExistingServer: true,
  },
});
