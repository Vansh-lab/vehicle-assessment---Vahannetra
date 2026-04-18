"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileUp, Flame, ShieldCheck } from "lucide-react";
import { useInspectionStore } from "@/store/inspection-store";
import { mockInspectionResult } from "@/lib/api/mock-data";
import { downloadInspectionReport, getNearbyGarages, submitClaim } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { AnnotatedImageViewer } from "@/components/results/annotated-image-viewer";
import { DamageCard } from "@/components/results/damage-card";
import { ConfidenceMeter } from "@/components/results/confidence-meter";
import { CostEstimateWidget } from "@/components/results/cost-estimate-widget";
import { CarHeatmap } from "@/components/advanced/CarHeatmap";
import { DSQChart } from "@/components/advanced/DSQChart";
import { PartGraph } from "@/components/advanced/PartGraph";
import { DamageReport } from "@/components/advanced/DamageReport";
import { NearbyServices } from "@/components/advanced/NearbyServices";
import { BeforeAfterSlider } from "@/components/advanced/BeforeAfterSlider";
import { useConfirm } from "@/components/providers/confirm-provider";
import { env } from "@/lib/env";

export default function ResultPage() {
  const [heatmapEnabled, setHeatmapEnabled] = useState(true);
  const [claimMessage, setClaimMessage] = useState("");
  const { confirm } = useConfirm();
  const bypassConfirm = env.E2E_BYPASS_CONFIRM;
  const { latestResult } = useInspectionStore();
  const result = latestResult ?? mockInspectionResult;

  const claimMutation = useMutation({
    mutationFn: () => submitClaim(result.inspectionId),
    onSuccess: (data) => {
      setClaimMessage(`Claim submitted: ${data.claim_id} (${data.provider_reference})`);
    },
    onError: (error) => {
      setClaimMessage(error instanceof Error ? error.message : "Claim submission failed");
    },
  });


  const downloadMutation = useMutation({
    mutationFn: () => downloadInspectionReport(result.inspectionId),
  });

  const confidence = useMemo(() => {
    if (!result.findings.length) return 0;
    const total = result.findings.reduce((sum, finding) => sum + finding.confidence, 0);
    return (total / result.findings.length) * 100;
  }, [result.findings]);

  const costRange = useMemo(
    () =>
      result.findings.reduce(
        (acc, finding) => ({ min: acc.min + finding.estimateMin, max: acc.max + finding.estimateMax }),
        { min: 0, max: 0 },
      ),
    [result.findings],
  );
  const groupedCount = useMemo(
    () =>
      result.findings.reduce<Record<string, number>>((acc, finding) => {
        acc[finding.type] = (acc[finding.type] ?? 0) + 1;
        return acc;
      }, {}),
    [result.findings],
  );
  const partGraphData = useMemo(
    () =>
      Object.entries(groupedCount).map(([part, impact]) => ({
        part,
        impact,
      })),
    [groupedCount],
  );
  const topDamageType = result.findings[0]?.type ?? "major";
  const scratchSummary = useMemo(() => {
    const scratchFindings = result.findings.filter((finding) => finding.type === "scratch");
    const total = scratchFindings.length;
    if (total === 0) {
      return {
        total: 0,
        avgConfidence: 0,
        hotspot: "No scratch hotspot detected",
        areaPct: 0,
      };
    }
    const avgConfidence = Math.round(
      (scratchFindings.reduce((sum, finding) => sum + finding.confidence, 0) / total) * 100,
    );
    const areaTotal = scratchFindings.reduce((sum, finding) => {
      const [x1, y1, x2, y2] = finding.box;
      return sum + Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    }, 0);
    const frameArea = Math.max(
      1,
      result.findings.reduce((maxArea, finding) => {
        const [x1, y1, x2, y2] = finding.box;
        return Math.max(maxArea, Math.max(0, x2) * Math.max(0, y2), Math.max(0, x1) * Math.max(0, y1));
      }, 1),
    );
    const avgXCenter = scratchFindings.reduce((sum, finding) => sum + (finding.box[0] + finding.box[2]) / 2, 0) / total;
    const hotspot = avgXCenter < 140 ? "Left side" : avgXCenter < 280 ? "Center" : "Right side";
    return {
      total,
      avgConfidence,
      hotspot,
      areaPct: Math.min(100, Math.round((areaTotal / frameArea) * 100)),
    };
  }, [result.findings]);

  const garagesQuery = useQuery({
    queryKey: ["nearby-garages", topDamageType],
    queryFn: () => getNearbyGarages({ lat: 19.07, lng: 72.87, sort: "smart_score", damageType: topDamageType }),
  });

  return (
    <div className="space-y-4 pb-4">
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-400">Vehicle Summary</p>
          <p className="text-lg font-semibold text-cyan-100">
            {result.vehicle.plate} • {result.vehicle.model} • {result.vehicle.type}
          </p>
          <p className="text-xs text-slate-400">Inspection ID: {result.inspectionId}</p>
        </div>
        <Badge className={result.triageCategory === "STRUCTURAL/FUNCTIONAL" ? "border-rose-300/30 bg-rose-500/20 text-rose-100" : ""}>
          {result.triageCategory}
        </Badge>
      </Card>

      <Card>
        <p className="mb-2 text-sm font-semibold text-slate-100">Damage count by category</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(groupedCount).map(([key, value]) => (
            <Badge key={key} className="border-white/20 bg-white/10 capitalize text-slate-200">
              {key}: {value}
            </Badge>
          ))}
        </div>
      </Card>

      <Card>
        <p className="mb-2 text-sm font-semibold text-slate-100">Scratch summary</p>
        <div className="grid gap-2 text-sm text-slate-200 md:grid-cols-2">
          <p>Total scratches: <span className="font-semibold text-cyan-100">{scratchSummary.total}</span></p>
          <p>Avg confidence: <span className="font-semibold text-cyan-100">{scratchSummary.avgConfidence}%</span></p>
          <p>Estimated scratch coverage: <span className="font-semibold text-cyan-100">{scratchSummary.areaPct}%</span></p>
          <p>Hotspot zone: <span className="font-semibold text-cyan-100">{scratchSummary.hotspot}</span></p>
        </div>
      </Card>

      <AnnotatedImageViewer imageUrl={result.processedImageUrl} findings={result.findings} heatmapEnabled={heatmapEnabled} />

      <Card className="flex items-center justify-between">
        <p className="text-sm text-slate-200">Heatmap visualization</p>
        <Switch checked={heatmapEnabled} onCheckedChange={setHeatmapEnabled} label="Heatmap toggle" />
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        <Card className="space-y-4">
          <ConfidenceMeter confidence={confidence} />
          <DSQChart score={100 - result.healthScore} />
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Flame size={16} className="text-amber-300" /> Severity badge: <Badge>{result.findings.some((item) => item.severity === "high") ? "High" : "Moderate"}</Badge>
          </div>
        </Card>
        <CostEstimateWidget min={costRange.min} max={costRange.max} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <CarHeatmap findings={result.findings} />
        <PartGraph items={partGraphData} />
      </div>

      <BeforeAfterSlider beforeUrl="/favicon.ico" afterUrl={result.processedImageUrl} beforeScore={100} afterScore={result.healthScore} />

      <NearbyServices
        items={garagesQuery.data ?? []}
        damageType={topDamageType}
      />

      <div className="grid gap-3">{result.findings.map((finding) => <DamageCard key={finding.id} finding={finding} />)}</div>

      <DamageReport findings={result.findings} />

      <Card>
        <p className="text-sm font-semibold text-slate-100">Explainability</p>
        <ul className="mt-2 space-y-2 text-sm text-slate-300">
          {result.findings.map((finding) => (
            <li key={`${finding.id}-exp`} className="rounded-xl border border-white/10 p-3">
              <span className="font-medium capitalize text-cyan-100">{finding.type}:</span> {finding.explainability}
            </li>
          ))}
        </ul>
      </Card>

      <div className="sticky bottom-16 grid gap-2 md:bottom-4 md:grid-cols-2">
        <Button
          variant="secondary"
          onClick={async () => {
            const accepted = bypassConfirm
              ? true
              : await confirm({
                  title: "Submit insurance claim",
                  message: "This action will submit the selected inspection to the external claims destination.",
                });
            if (accepted) claimMutation.mutate();
          }}
          disabled={claimMutation.isPending}
        >
          <FileUp size={16} className="mr-2" /> {claimMutation.isPending ? "Submitting claim..." : "Send to claim system"}
        </Button>
        <Button
          className="w-full"
          onClick={async () => {
            const accepted = bypassConfirm
              ? true
              : await confirm({
                  title: "Download inspection report",
                  message: "A signed report PDF will be generated/downloaded for this inspection.",
                });
            if (accepted) downloadMutation.mutate();
          }}
          disabled={downloadMutation.isPending}
        >
          <Download size={16} className="mr-2" /> {downloadMutation.isPending ? "Preparing report..." : "Download report"}
        </Button>
      </div>

      {claimMessage ? <Card><p className="text-xs text-slate-300">{claimMessage}</p></Card> : null}

      <Card className="border-cyan-400/20">
        <p className="flex items-center gap-2 text-sm text-cyan-100">
          <ShieldCheck size={16} /> AI result confidence & explainability included for auditor trust.
        </p>
      </Card>
    </div>
  );
}
