"use client";

import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { I18nProvider } from "@/components/providers/i18n-provider";
import { ConfirmProvider } from "@/components/providers/confirm-provider";
import { ClientTelemetry } from "@/components/providers/client-telemetry";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <ThemeProvider>
      <I18nProvider>
        <ConfirmProvider>
          <QueryClientProvider client={queryClient}>
            <ClientTelemetry />
            {children}
          </QueryClientProvider>
        </ConfirmProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
