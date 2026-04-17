"use client";

import { useEffect } from "react";
import { API_BASE_URL } from "@/lib/api/client";

async function sendClientError(payload: {
  level: "error" | "warning";
  message: string;
  source?: string;
  stack?: string;
  route?: string;
}) {
  try {
    await fetch(`${API_BASE_URL}/telemetry/client-error`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...payload,
        user_agent: navigator.userAgent,
      }),
      keepalive: true,
    });
  } catch {
    if (process.env.NODE_ENV !== "production") {
      console.warn("Client telemetry send failed");
    }
  }
}

export function ClientTelemetry() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      void sendClientError({
        level: "error",
        message: event.message || "Unhandled client error",
        source: event.filename,
        stack: event.error?.stack,
        route: window.location.pathname,
      });
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? event.reason.message : String(event.reason ?? "Unknown rejection");
      const stack = event.reason instanceof Error ? event.reason.stack : undefined;
      void sendClientError({
        level: "error",
        message: reason,
        stack,
        route: window.location.pathname,
      });
    };

    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  return null;
}
