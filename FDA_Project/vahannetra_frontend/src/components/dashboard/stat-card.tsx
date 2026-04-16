import { Card } from "@/components/ui/card";

export function StatCard({ title, value, hint }: { title: string; value: string | number; hint: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-2 text-2xl font-bold text-slate-100">{value}</p>
      <p className="mt-1 text-xs text-slate-400">{hint}</p>
    </Card>
  );
}
