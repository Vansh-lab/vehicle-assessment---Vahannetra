"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useInspectionStore } from "@/store/inspection-store";
import { assessDamageMock, assessDamageWithBackend } from "@/lib/api/services";

const stages = ["Preprocessing image", "Detection", "Classification", "Severity scoring"];

export default function ProcessingPage() {
  const router = useRouter();
  const [progress, setProgress] = useState(8);
  const [status, setStatus] = useState<string>(stages[0]);
  const [error, setError] = useState("");
  const { selectedFile, plate, model, vin, vehicleType, selectedAngles, setResult } = useInspectionStore();

  const payload = useMemo(() => ({ vehicleType, plate, model, vin, angles: selectedAngles }), [model, plate, selectedAngles, vehicleType, vin]);

  useEffect(() => {
    if (!selectedFile) {
      router.push("/inspection/new");
      return;
    }

    let cancelled = false;

    const ticker = setInterval(() => {
      setProgress((prev) => {
        const next = Math.min(95, prev + 9);
        setStatus(stages[Math.min(stages.length - 1, Math.floor(next / 25))]);
        return next;
      });
    }, 500);

    const run = async () => {
      try {
        const response = process.env.NEXT_PUBLIC_USE_BACKEND === "true" ? await assessDamageWithBackend(selectedFile, payload) : await assessDamageMock(payload);
        if (cancelled) return;
        setResult(response);
        setProgress(100);
        setStatus("Analysis complete");
        setTimeout(() => router.push("/inspection/result"), 700);
      } catch {
        if (cancelled) return;
        setError("API failure. Please retry after checking network or backend status.");
      } finally {
        clearInterval(ticker);
      }
    };

    run();

    return () => {
      cancelled = true;
      clearInterval(ticker);
    };
  }, [payload, router, selectedFile, setResult]);

  return (
    <div className="mx-auto max-w-xl space-y-4 pt-10">
      <Card className="space-y-5 text-center">
        <motion.div animate={{ scale: [1, 1.07, 1] }} transition={{ duration: 1.6, repeat: Number.POSITIVE_INFINITY }} className="mx-auto h-16 w-16 rounded-full bg-cyan-400/20 shadow-[0_0_30px_rgba(0,229,255,0.35)]" />
        <div>
          <p className="text-xl font-semibold text-cyan-100">Analyzing Damage…</p>
          <p className="text-sm text-slate-400">{status}</p>
        </div>
        <Progress value={progress} />
        <p className="text-xs text-slate-400">{progress}% complete</p>
      </Card>
      {error ? <Card className="border-rose-400/30"><p className="text-sm text-rose-200">{error}</p></Card> : null}
    </div>
  );
}
