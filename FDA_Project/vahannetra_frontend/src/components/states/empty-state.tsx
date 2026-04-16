import { SearchX } from "lucide-react";
import { Card } from "@/components/ui/card";

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Card className="text-center py-10">
      <SearchX className="mx-auto mb-3 text-cyan-300" />
      <p className="text-lg font-semibold text-slate-100">{title}</p>
      <p className="mt-1 text-sm text-slate-400">{description}</p>
    </Card>
  );
}
