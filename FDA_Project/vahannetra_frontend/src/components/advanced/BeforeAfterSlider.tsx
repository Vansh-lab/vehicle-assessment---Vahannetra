"use client";

import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";

interface BeforeAfterSliderProps {
  beforeUrl: string;
  afterUrl: string;
  beforeScore?: number;
  afterScore?: number;
}

export function BeforeAfterSlider({ beforeUrl, afterUrl, beforeScore = 0, afterScore = 0 }: BeforeAfterSliderProps) {
  const [position, setPosition] = useState(55);
  const deltaPct = useMemo(() => {
    if (beforeScore <= 0) return 0;
    return Math.round(((afterScore - beforeScore) / beforeScore) * 100);
  }, [afterScore, beforeScore]);

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-100">Before / After</p>
        <p className="text-xs text-slate-300">Damage delta: {deltaPct >= 0 ? `+${deltaPct}` : deltaPct}%</p>
      </div>
      <div className="relative h-52 overflow-hidden rounded-xl border border-white/15">
        <img src={beforeUrl} alt="Before inspection" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 overflow-hidden" style={{ width: `${position}%` }}>
          <img src={afterUrl} alt="After inspection" className="h-full w-full object-cover" />
        </div>
        <div className="absolute inset-y-0 w-0.5 bg-cyan-300" style={{ left: `${position}%` }} />
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={position}
        onChange={(event) => setPosition(Number(event.target.value))}
        className="w-full"
      />
    </Card>
  );
}
