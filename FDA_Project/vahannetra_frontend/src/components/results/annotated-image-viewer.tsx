"use client";

import { useMemo } from "react";
import type { DamageFinding } from "@/types/domain";

interface AnnotatedImageViewerProps {
  imageUrl: string;
  findings: DamageFinding[];
  heatmapEnabled: boolean;
}

export function AnnotatedImageViewer({ imageUrl, findings, heatmapEnabled }: AnnotatedImageViewerProps) {
  const referenceBounds = useMemo(() => {
    const maxX = Math.max(...findings.map((item) => item.box[2]), 1);
    const maxY = Math.max(...findings.map((item) => item.box[3]), 1);
    return { width: maxX, height: maxY };
  }, [findings]);

  const overlays = useMemo(
    () =>
      findings.map((item) => {
        const [x1, y1, x2, y2] = item.box;
        const width = Math.max(0, x2 - x1);
        const height = Math.max(0, y2 - y1);
        return {
          id: item.id,
          label: `${item.type} ${(item.confidence * 100).toFixed(0)}%`,
          left: `${(x1 / referenceBounds.width) * 100}%`,
          top: `${(y1 / referenceBounds.height) * 100}%`,
          width: `${(width / referenceBounds.width) * 100}%`,
          height: `${(height / referenceBounds.height) * 100}%`,
          color: item.severity === "high" ? "#ff5a7a" : item.severity === "medium" ? "#ffb648" : "#35d48d",
        };
      }),
    [findings, referenceBounds.height, referenceBounds.width],
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
        >
          <span
            className="absolute -top-6 left-0 rounded bg-slate-950/80 px-1.5 py-0.5 text-[10px] font-medium capitalize text-slate-100"
            style={{ border: `1px solid ${overlay.color}` }}
          >
            {overlay.label}
          </span>
        </div>
      ))}
    </div>
  );
}
