import { Card } from "@/components/ui/card";

interface PartGraphItem {
  part: string;
  impact: number;
}

interface PartGraphProps {
  items: PartGraphItem[];
}

export function PartGraph({ items }: PartGraphProps) {
  const max = Math.max(1, ...items.map((item) => item.impact));
  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">Part Impact Graph</p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.part} className="space-y-1">
            <div className="flex items-center justify-between text-xs text-slate-300">
              <span>{item.part}</span>
              <span>{item.impact}</span>
            </div>
            <div className="h-2 rounded bg-white/10">
              <div className="h-2 rounded bg-cyan-400/70" style={{ width: `${(item.impact / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
