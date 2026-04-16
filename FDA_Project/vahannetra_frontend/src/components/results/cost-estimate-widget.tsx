import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

export function CostEstimateWidget({ min, max }: { min: number; max: number }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-400">Estimated Repair Range</p>
      <p className="mt-2 text-2xl font-bold text-emerald-100">
        {formatCurrency(min)} - {formatCurrency(max)}
      </p>
      <p className="mt-1 text-xs text-slate-400">Includes panel + paint assumptions from similar historical jobs.</p>
    </Card>
  );
}
