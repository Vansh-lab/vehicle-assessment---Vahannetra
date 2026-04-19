"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { downloadInspectionReport, getInspectionDetail } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { downloadFallbackInspectionPdf } from "@/lib/reports/fallback-pdf";

export default function HistoryDetailPage() {
  const params = useParams<{ id: string }>();
  const id = typeof params.id === "string" ? params.id : "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["inspection-detail", id],
    queryFn: () => getInspectionDetail(id),
    enabled: !!id,
  });

  const downloadMutation = useMutation({
    mutationFn: async () => downloadInspectionReport(id),
    onSuccess: (url) => {
      window.open(url, "_blank", "noopener,noreferrer");
    },
    onError: async () => {
      if (!data) return;
      await downloadFallbackInspectionPdf(data);
    },
  });

  if (isLoading) return <Skeleton className="h-44" />;
  if (isError || !data) return <ErrorState message="Failed to load inspection detail." onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-lg font-semibold text-slate-100">Detailed Report • {data.inspectionId}</p>
        <p className="text-sm text-slate-400">
          {data.vehicle.plate} • {data.vehicle.model}
        </p>
        <Badge className="mt-2">{data.triageCategory}</Badge>
      </Card>
      <Card>
        <p className="text-sm font-semibold text-slate-100">AI Summary</p>
        <p className="mt-2 text-sm text-slate-300">Health score: {data.healthScore}</p>
        <p className="text-sm text-slate-300">Detected findings: {data.findings.length}</p>
        <p className="text-sm text-slate-300">Inspected at: {new Date(data.vehicle.inspectedAt).toLocaleString()}</p>
      </Card>
      <div className="grid gap-2 sm:grid-cols-2">
        <Button className="w-full" onClick={() => downloadMutation.mutate()} disabled={downloadMutation.isPending}>
          {downloadMutation.isPending ? "Preparing PDF..." : "Download PDF report"}
        </Button>
        <Link href="/inspection/result">
          <Button variant="secondary" className="w-full">
            Open visual diagnostics
          </Button>
        </Link>
      </div>
    </div>
  );
}
