import type { DamageFinding } from "@/types/domain";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";

export function DamageCard({ finding }: { finding: DamageFinding }) {
  const [x1, y1, x2, y2] = finding.box;
  const width = Math.max(0, x2 - x1);
  const height = Math.max(0, y2 - y1);
  const centerX = Math.round((x1 + x2) / 2);
  const centerY = Math.round((y1 + y2) / 2);

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold capitalize text-slate-100">{finding.type}</p>
        <Badge className="capitalize">{finding.severity}</Badge>
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge className="border-white/20 bg-white/10 text-slate-200">{finding.category}</Badge>
        <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">
          Confidence {(finding.confidence * 100).toFixed(0)}%
        </Badge>
      </div>
      <p className="text-xs text-slate-300">{finding.explainability}</p>
      <p className="text-xs text-slate-300">Center: ({centerX}px, {centerY}px) • Box: {Math.round(width)} × {Math.round(height)} px</p>
      <p className="text-sm font-medium text-cyan-100">
        Estimate {formatCurrency(finding.estimateMin)} - {formatCurrency(finding.estimateMax)}
      </p>
    </Card>
  );
}
