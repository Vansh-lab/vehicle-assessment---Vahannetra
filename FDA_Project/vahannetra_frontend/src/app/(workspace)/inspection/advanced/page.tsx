"use client";

import { mockInspectionResult } from "@/lib/api/mock-data";
import { Card } from "@/components/ui/card";
import { DSQChart } from "@/components/advanced/DSQChart";
import { CarHeatmap } from "@/components/advanced/CarHeatmap";
import { DamageReport } from "@/components/advanced/DamageReport";
import { PartGraph } from "@/components/advanced/PartGraph";
import { NearbyServices } from "@/components/advanced/NearbyServices";
import { BeforeAfterSlider } from "@/components/advanced/BeforeAfterSlider";

export default function AdvancedInspectionPage() {
  const result = mockInspectionResult;
  const grouped = result.findings.reduce<Record<string, number>>((acc, item) => {
    acc[item.type] = (acc[item.type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="grid gap-3 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
      <div className="space-y-3">
        <DSQChart score={100 - result.healthScore} />
        <PartGraph items={Object.entries(grouped).map(([part, impact]) => ({ part, impact }))} />
      </div>
      <div className="space-y-3">
        <BeforeAfterSlider beforeUrl={result.processedImageUrl} afterUrl={result.processedImageUrl} />
        <CarHeatmap findings={result.findings} />
        <NearbyServices
          items={[
            { id: "g1", name: "AutoFix Prime", distanceKm: 2.1, dent: "₹3k-₹6k", scratch: "₹1k-₹2.5k", paint: "₹4k-₹8k", rating: 4.5 },
            { id: "g2", name: "Shield Motors", distanceKm: 3.4, dent: "₹2.8k-₹5.8k", scratch: "₹900-₹2.2k", paint: "₹3.8k-₹7.5k", rating: 4.3 },
          ]}
        />
      </div>
      <div className="space-y-3">
        <DamageReport findings={result.findings} />
        <Card>
          <p className="text-sm text-slate-300">3-panel inspector workspace scaffold (left insights, center visuals, right report).</p>
        </Card>
      </div>
    </div>
  );
}
