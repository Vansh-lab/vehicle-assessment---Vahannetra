"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isSessionActive } from "@/lib/auth/session";
import { Card } from "@/components/ui/card";

export function AuthGuard({ children }: { children: ReactNode }) {
  const bypassAuth = process.env.NEXT_PUBLIC_E2E_BYPASS_AUTH === "true";
  const router = useRouter();
  const active = isSessionActive();

  useEffect(() => {
    if (!bypassAuth && !active) {
      router.replace("/login");
    }
  }, [active, bypassAuth, router]);

  if (bypassAuth) {
    return <>{children}</>;
  }

  if (!active) {
    return (
      <Card className="mt-8">
        <p className="text-sm text-slate-300">Redirecting to login…</p>
      </Card>
    );
  }

  return <>{children}</>;
}
