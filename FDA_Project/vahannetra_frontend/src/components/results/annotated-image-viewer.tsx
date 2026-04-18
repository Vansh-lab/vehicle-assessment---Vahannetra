"use client";

import { useMemo, useState } from "react";
import type { DamageFinding } from "@/types/domain";

interface AnnotatedImageViewerProps {
  imageUrl: string;
  findings: DamageFinding[];
  heatmapEnabled: boolean;
}

export function AnnotatedImageViewer({ imageUrl, findings, heatmapEnabled }: AnnotatedImageViewerProps) {
  const [imageDims, setImageDims] = useState({ width: 420, height: 280 });

  const overlays = useMemo(
    () =>
      findings.map((item) => {
        const [x1, y1, x2, y2] = item.box;
        const width = Math.max(1, imageDims.width);
        const height = Math.max(1, imageDims.height);
        const left = Math.max(0, Math.min(100, (x1 / width) * 100));
        const top = Math.max(0, Math.min(100, (y1 / height) * 100));
        const boxWidth = Math.max(1, Math.min(100 - left, ((x2 - x1) / width) * 100));
        const boxHeight = Math.max(1, Math.min(100 - top, ((y2 - y1) / height) * 100));

        return {
          id: item.id,
          label: `${item.type} (${Math.round(item.confidence * 100)}%)`,
          left: `${left}%`,
          top: `${top}%`,
          width: `${boxWidth}%`,
          height: `${boxHeight}%`,
          color: item.severity === "high" ? "#ff5a7a" : item.severity === "medium" ? "#ffb648" : "#35d48d",
        };
      }),
    [findings, imageDims.height, imageDims.width],
  );

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950/70">
      <img
        src={imageUrl}
        alt="Annotated vehicle"
        className="h-64 w-full object-cover md:h-80"
        onLoad={(event) => {
          const target = event.currentTarget;
          const nextWidth = target.naturalWidth || 420;
          const nextHeight = target.naturalHeight || 280;
          setImageDims({ width: nextWidth, height: nextHeight });
        }}
      />

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
          <span className="absolute -top-5 left-0 rounded bg-slate-950/90 px-1.5 py-0.5 text-[10px] capitalize text-cyan-100">
            {overlay.label}
          </span>
        </div>
      ))}

      {findings.length === 0 ? (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/45">
          <p className="rounded bg-slate-950/80 px-3 py-2 text-xs text-slate-200">No visible damage boxes detected from this upload.</p>
        </div>
      ) : null}
    </div>
  );
}
