import type { DamageFinding } from "@/types/domain";
import { Card } from "@/components/ui/card";

interface DamageReportProps {
  findings: DamageFinding[];
}

export function DamageReport({ findings }: DamageReportProps) {
  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-slate-100">Damage Report</p>
      <ul className="space-y-2 text-xs text-slate-300">
        {findings.map((finding) => (
          <li key={finding.id} className="rounded-lg border border-white/10 px-3 py-2">
            <p className="font-medium capitalize text-slate-200">{finding.type}</p>
            <p>
              Severity: {finding.severity} • Confidence: {Math.round(finding.confidence * 100)}%
            </p>
            <p>
              Region: ({Math.round((finding.box[0] + finding.box[2]) / 2)}, {Math.round((finding.box[1] + finding.box[3]) / 2)}) • Box: {Math.round(Math.max(0, finding.box[2] - finding.box[0]))}×{Math.round(Math.max(0, finding.box[3] - finding.box[1]))} px
            </p>
            <p>
              Estimate: ₹{finding.estimateMin.toLocaleString()} - ₹{finding.estimateMax.toLocaleString()}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
