"use client";

import { useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";

interface DSQChartProps {
  score: number;
}

export function DSQChart({ score }: DSQChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const clamped = Math.max(0, Math.min(100, score));
    const angle = (Math.PI * clamped) / 100;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.lineWidth = 16;
    ctx.strokeStyle = "rgba(148,163,184,0.25)";
    ctx.beginPath();
    ctx.arc(120, 120, 72, Math.PI, 2 * Math.PI);
    ctx.stroke();

    ctx.strokeStyle = clamped > 70 ? "#f43f5e" : clamped > 35 ? "#f59e0b" : "#22c55e";
    ctx.beginPath();
    ctx.arc(120, 120, 72, Math.PI, Math.PI + angle);
    ctx.stroke();

    ctx.fillStyle = "#e2e8f0";
    ctx.font = "bold 28px sans-serif";
    ctx.fillText(`${Math.round(clamped)}`, 95, 126);
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "#94a3b8";
    ctx.fillText("DSQ v2", 103, 146);
  }, [score]);

  return (
    <Card className="space-y-2">
      <p className="text-sm font-semibold text-slate-100">Damage Severity Quotient</p>
      <canvas ref={canvasRef} width={240} height={170} className="mx-auto" />
    </Card>
  );
}
