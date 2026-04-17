"use client";

import { type MouseEvent, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import Link from "next/link";
import { downloadInspectionReport, getHistory } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useConfirm } from "@/components/providers/confirm-provider";

export default function HistoryPage() {
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dateFilter, setDateFilter] = useState("");
  const { confirm } = useConfirm();
  const bypassConfirm = process.env.NEXT_PUBLIC_E2E_BYPASS_CONFIRM === "true";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["history", search, severityFilter, statusFilter, dateFilter],
    queryFn: () => getHistory({ search, severity: severityFilter, status: statusFilter, date: dateFilter }),
  });

  const filtered = useMemo(() => data ?? [], [data]);

  const handleDownload = async (inspectionId: string, event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const accepted = bypassConfirm
      ? true
      : await confirm({
          title: "Download report PDF",
          message: "This will generate and open the signed inspection PDF report.",
        });
    if (!accepted) return;
    const url = await downloadInspectionReport(inspectionId);
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <p className="text-lg font-semibold text-slate-100">Inspection History</p>
        <div className="grid gap-2 sm:grid-cols-4">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search vehicle / plate" />
          <select
            aria-label="severity-filter"
            className="h-11 rounded-xl border border-white/15 bg-slate-950/70 px-3 text-sm text-slate-100"
            value={severityFilter}
            onChange={(event) => setSeverityFilter(event.target.value)}
          >
            <option value="all">All severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <select
            aria-label="status-filter"
            className="h-11 rounded-xl border border-white/15 bg-slate-950/70 px-3 text-sm text-slate-100"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="all">All status</option>
            <option value="Completed">Completed</option>
            <option value="Pending">Pending</option>
            <option value="Failed">Failed</option>
          </select>
          <Input type="date" aria-label="date-filter" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
        </div>
      </Card>

      {isLoading ? <Skeleton className="h-40" /> : null}
      {isError ? <ErrorState message="Failed to load history." onRetry={() => refetch()} /> : null}
      {!isLoading && !isError && filtered.length === 0 ? (
        <EmptyState title="No inspections found" description="Try adjusting date or severity filters." />
      ) : null}

      <div className="space-y-3">
        {filtered.map((item) => (
          <Link key={item.id} href={`/history/${item.id}`}>
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    {item.plate} • {item.model}
                  </p>
                  <p className="text-xs text-slate-400">
                    {new Date(item.date).toLocaleString()} • Status: {item.status}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className="capitalize">{item.severity}</Badge>
                  <Button size="sm" variant="secondary" onClick={(event) => void handleDownload(item.id, event)}>
                    <Download size={14} className="mr-1" /> PDF
                  </Button>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
