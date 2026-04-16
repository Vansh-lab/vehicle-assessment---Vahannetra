import { Progress } from "@/components/ui/progress";

export function ConfidenceMeter({ confidence }: { confidence: number }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-slate-300">AI Confidence</span>
        <span className="font-semibold text-cyan-100">{confidence.toFixed(0)}%</span>
      </div>
      <Progress value={confidence} />
    </div>
  );
}
