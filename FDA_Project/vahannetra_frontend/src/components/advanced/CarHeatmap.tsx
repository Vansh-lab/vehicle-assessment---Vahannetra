"use client";

import type { DamageFinding } from "@/types/domain";
import { Card } from "@/components/ui/card";

interface CarHeatmapProps {
  findings: DamageFinding[];
}

export function CarHeatmap({ findings }: CarHeatmapProps) {
  return (
    <Card className="space-y-2">
      <p className="text-sm font-semibold text-slate-100">Car Heatmap</p>
      <div className="relative h-52 rounded-xl border border-white/15 bg-slate-900/50">
        {findings.map((finding) => {
          const [x, y, w, h] = finding.box;
          return (
            <div
              key={finding.id}
              className="absolute rounded border border-rose-300/70 bg-rose-500/25"
              style={{
                left: `${Math.max(0, Math.min(95, x / 6))}%`,
                top: `${Math.max(0, Math.min(95, y / 6))}%`,
                width: `${Math.max(6, Math.min(28, w / 8))}%`,
                height: `${Math.max(6, Math.min(22, h / 10))}%`,
              }}
              title={`${finding.type} (${Math.round(finding.confidence * 100)}%)`}
            />
          );
        })}
      </div>
    </Card>
  );
}
