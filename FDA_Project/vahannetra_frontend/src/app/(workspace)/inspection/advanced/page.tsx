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
            {
              id: "g1",
              name: "AutoFix Prime",
              address: "Andheri East, Mumbai",
              city: "Mumbai",
              distance_km: 2.1,
              rating: 4.5,
              is_open_now: true,
              smart_score: 82,
              services: ["Dent repair", "Paint work"],
              pricing: {
                scratch: { min: 1500, max: 3200 },
                dent: { min: 3400, max: 7800 },
                paint: { min: 4200, max: 8500 },
                major: { min: 15000, max: 31000 },
              },
              market_comparison: { dent: { market_avg: 8000, delta_pct: -8, verdict: "below_market" } },
              price_badge: "BELOW MARKET",
            },
            {
              id: "g2",
              name: "Shield Motors",
              address: "Powai, Mumbai",
              city: "Mumbai",
              distance_km: 3.4,
              rating: 4.3,
              is_open_now: true,
              smart_score: 78,
              services: ["Scratch", "Dent", "Insurance approved"],
              pricing: {
                scratch: { min: 1800, max: 3600 },
                dent: { min: 3600, max: 8200 },
                paint: { min: 4300, max: 8800 },
                major: { min: 16000, max: 32000 },
              },
            },
          ]}
          damageType={result.findings[0]?.type}
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
