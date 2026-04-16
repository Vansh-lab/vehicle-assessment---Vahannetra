"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import Link from "next/link";
import { getHistory } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryPage() {
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["history"], queryFn: getHistory });

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.filter((item) => {
      const matchSearch = `${item.plate} ${item.model}`.toLowerCase().includes(search.toLowerCase());
      const matchSeverity = severityFilter === "all" || item.severity === severityFilter;
      return matchSearch && matchSeverity;
    });
  }, [data, search, severityFilter]);

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <p className="text-lg font-semibold text-slate-100">Inspection History</p>
        <div className="grid gap-2 sm:grid-cols-3">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search vehicle / plate" />
          <select aria-label="severity-filter" className="h-11 rounded-xl border border-white/15 bg-slate-950/70 px-3 text-sm text-slate-100" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            <option value="all">All severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <Input type="date" aria-label="date-filter" />
        </div>
      </Card>

      {isLoading ? <Skeleton className="h-40" /> : null}
      {isError ? <ErrorState message="Failed to load history." onRetry={() => refetch()} /> : null}
      {!isLoading && !isError && filtered.length === 0 ? <EmptyState title="No inspections found" description="Try adjusting date or severity filters." /> : null}

      <div className="space-y-3">
        {filtered.map((item) => (
          <Link key={item.id} href={`/history/${item.id}`}><Card>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-100">{item.plate} • {item.model}</p>
                <p className="text-xs text-slate-400">{new Date(item.date).toLocaleString()} • Status: {item.status}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="capitalize">{item.severity}</Badge>
                <Button size="sm" variant="secondary"><Download size={14} className="mr-1" /> PDF</Button>
              </div>
            </div>
          </Card></Link>
        ))}
      </div>
    </div>
  );
}
