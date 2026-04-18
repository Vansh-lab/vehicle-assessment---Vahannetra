"use client";

import { useMemo, useState } from "react";
import type { NearbyGarage } from "@/lib/api/types";
import { Card } from "@/components/ui/card";

interface NearbyServicesProps {
  items: NearbyGarage[];
  damageType?: string;
}

function getDamageKey(damageType?: string): "scratch" | "dent" | "paint" | "major" {
  const normalized = (damageType || "").toLowerCase();
  if (normalized.includes("dent")) return "dent";
  if (normalized.includes("paint")) return "paint";
  if (normalized.includes("scratch")) return "scratch";
  return "major";
}

function sortByCheapest(garages: NearbyGarage[], damageType?: string) {
  const key = getDamageKey(damageType);
  return [...garages].sort((a, b) => (a.pricing?.[key]?.min || 99999) - (b.pricing?.[key]?.min || 99999));
}

function PricingTable({
  pricing,
  marketComparison,
  damageType,
}: {
  pricing: NearbyGarage["pricing"];
  marketComparison?: NearbyGarage["market_comparison"];
  damageType?: string;
}) {
  const activeKey = getDamageKey(damageType);
  const rows = [
    { key: "scratch", label: "Scratch repair" },
    { key: "dent", label: "Dent repair" },
    { key: "paint", label: "Paint work" },
    { key: "major", label: "Major body work" },
  ] as const;

  return (
    <table className="w-full text-xs text-slate-300">
      <thead>
        <tr className="text-left text-slate-400">
          <th className="py-1 pr-2">Service</th>
          <th className="py-1 pr-2">Our Range</th>
          <th className="py-1 pr-2">Market Avg</th>
          <th className="py-1 pr-2">Delta</th>
          <th className="py-1 pr-2">Verdict</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const selected = activeKey === row.key;
          const market = marketComparison?.[row.key];
          return (
            <tr key={row.key} className={selected ? "bg-cyan-400/10" : "border-t border-white/10"}>
              <td className="py-1 pr-2">{row.label}</td>
              <td className="py-1 pr-2">₹{pricing[row.key].min.toLocaleString()} - ₹{pricing[row.key].max.toLocaleString()}</td>
              <td className="py-1 pr-2">{market ? `₹${market.market_avg.toLocaleString()}` : "-"}</td>
              <td className="py-1 pr-2">{market ? `${market.delta_pct}%` : "-"}</td>
              <td className="py-1 pr-2 uppercase">{market?.verdict?.replace("_", " ") || "-"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function NearbyServices({ items, damageType }: NearbyServicesProps) {
  const [sortMode, setSortMode] = useState<"smart" | "cheapest">("smart");
  const sorted = useMemo(
    () => (sortMode === "cheapest" ? sortByCheapest(items, damageType) : [...items].sort((a, b) => b.smart_score - a.smart_score)),
    [damageType, items, sortMode],
  );

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-100">Nearby Services Pricing Matrix</p>
        <select
          className="rounded border border-white/20 bg-slate-900 px-2 py-1 text-xs text-slate-200"
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value === "cheapest" ? "cheapest" : "smart")}
        >
          <option value="smart">Smart score</option>
          <option value="cheapest">Cheapest ({getDamageKey(damageType)})</option>
        </select>
      </div>

      <div className="space-y-3">
        {sorted.map((item) => (
          <div key={item.id} className="rounded-xl border border-white/10 p-3">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-slate-100">
                {item.name} • {item.distance_km.toFixed(1)} km • ⭐ {item.rating.toFixed(1)}
              </p>
              {item.price_badge ? <span className="rounded-full bg-cyan-500/20 px-2 py-0.5 text-[10px] text-cyan-100">{item.price_badge}</span> : null}
            </div>
            <PricingTable pricing={item.pricing} marketComparison={item.market_comparison} damageType={damageType} />
          </div>
        ))}
      </div>
    </Card>
  );
}
