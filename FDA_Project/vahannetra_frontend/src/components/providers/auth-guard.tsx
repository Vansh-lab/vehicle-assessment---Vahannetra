"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isSessionActive } from "@/lib/auth/session";
import { Card } from "@/components/ui/card";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const active = isSessionActive();

  useEffect(() => {
    if (!active) {
      router.replace("/login");
    }
  }, [active, router]);

  if (!active) {
    return (
      <Card className="mt-8">
        <p className="text-sm text-slate-300">Redirecting to login…</p>
      </Card>
    );
  }

  return <>{children}</>;
}
