"use client";

import { useMemo } from "react";
import type { DamageFinding } from "@/types/domain";

interface AnnotatedImageViewerProps {
  imageUrl: string;
  findings: DamageFinding[];
  heatmapEnabled: boolean;
}

export function AnnotatedImageViewer({ imageUrl, findings, heatmapEnabled }: AnnotatedImageViewerProps) {
  const overlays = useMemo(
    () =>
      findings.map((item) => {
        const [x1, y1, x2, y2] = item.box;
        return {
          id: item.id,
          left: `${(x1 / 420) * 100}%`,
          top: `${(y1 / 280) * 100}%`,
          width: `${((x2 - x1) / 420) * 100}%`,
          height: `${((y2 - y1) / 280) * 100}%`,
          color: item.severity === "high" ? "#ff5a7a" : item.severity === "medium" ? "#ffb648" : "#35d48d",
        };
      }),
    [findings],
  );

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950/70">
      <img src={imageUrl} alt="Annotated vehicle" className="h-64 w-full object-cover md:h-80" />

      {heatmapEnabled ? <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_45%,rgba(255,90,122,0.28),transparent_35%),radial-gradient(circle_at_65%_42%,rgba(255,182,72,0.26),transparent_30%)]" /> : null}

      {overlays.map((overlay) => (
        <div
          key={overlay.id}
          className="absolute rounded-md border-2"
          style={{
            left: overlay.left,
            top: overlay.top,
            width: overlay.width,
            height: overlay.height,
            borderColor: overlay.color,
            boxShadow: `0 0 12px ${overlay.color}`,
          }}
          aria-label={`damage-box-${overlay.id}`}
        />
      ))}
    </div>
  );
}
