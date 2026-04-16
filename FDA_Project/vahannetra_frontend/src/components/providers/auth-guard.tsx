"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isSessionActive } from "@/lib/auth/session";
import { Card } from "@/components/ui/card";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    const active = isSessionActive();
    setAllowed(active);
    setReady(true);
    if (!active) {
      router.replace("/login");
    }
  }, [router]);

  if (!ready) {
    return (
      <Card className="mt-8">
        <p className="text-sm text-slate-300">Checking session…</p>
      </Card>
    );
  }

  if (!allowed) return null;
  return <>{children}</>;
}
