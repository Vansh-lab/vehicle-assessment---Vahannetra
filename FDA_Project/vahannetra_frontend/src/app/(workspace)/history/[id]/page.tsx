import Link from "next/link";
import { notFound } from "next/navigation";
import { mockInspectionResult, mockRecentInspections } from "@/lib/api/mock-data";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default async function HistoryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const inspection = mockRecentInspections.find((item) => item.id === id);
  if (!inspection) notFound();

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-lg font-semibold text-slate-100">Detailed Report • {inspection.id}</p>
        <p className="text-sm text-slate-400">{inspection.plate} • {inspection.model}</p>
        <Badge className="mt-2 capitalize">{inspection.severity}</Badge>
      </Card>
      <Card>
        <p className="text-sm font-semibold text-slate-100">AI Summary</p>
        <p className="mt-2 text-sm text-slate-300">Health score: {mockInspectionResult.healthScore}</p>
        <p className="text-sm text-slate-300">Triage category: {mockInspectionResult.triageCategory}</p>
        <p className="text-sm text-slate-300">Detected findings: {mockInspectionResult.findings.length}</p>
      </Card>
      <div className="grid gap-2 sm:grid-cols-2">
        <Button>Download PDF report</Button>
        <Link href="/inspection/result"><Button variant="secondary" className="w-full">Open visual diagnostics</Button></Link>
      </div>
    </div>
  );
}
