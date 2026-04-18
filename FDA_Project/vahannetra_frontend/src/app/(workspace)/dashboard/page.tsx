"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, TriangleAlert } from "lucide-react";
import { getFleetHealth, getRecentInspections } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/dashboard/stat-card";
import { ErrorState } from "@/components/states/error-state";

export default function DashboardPage() {
  const healthQuery = useQuery({ queryKey: ["fleet-health"], queryFn: getFleetHealth });
  const inspectionsQuery = useQuery({ queryKey: ["recent-inspections"], queryFn: getRecentInspections });

  if (healthQuery.isLoading || inspectionsQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (healthQuery.isError || inspectionsQuery.isError || !healthQuery.data || !inspectionsQuery.data) {
    return <ErrorState message="Dashboard data unavailable. Check API/network and retry." />;
  }

  return (
    <div className="space-y-4">
      <Card className="border-cyan-400/30">
        <p className="text-sm text-slate-300">Fleet Health Score</p>
        <p className="mt-1 text-4xl font-bold text-cyan-100">{healthQuery.data.score}</p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400 sm:grid-cols-4">
          <span>{healthQuery.data.inspectionsToday} inspections today</span>
          <span>{healthQuery.data.attentionVehicles} requiring attention</span>
          <span>{healthQuery.data.activeAlerts} active alerts</span>
          <span>AI confidence stabilized</span>
        </div>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Recent inspections" value={inspectionsQuery.data.length} hint="Last 24 hours" />
        <StatCard title="Pending reviews" value={5} hint="Human QA queue" />
        <StatCard title="Critical damages" value={3} hint="High severity" />
        <StatCard title="Avg repair estimate" value="₹8.7K" hint="Rolling 7-day" />
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-slate-100">Vehicles requiring attention</p>
          <TriangleAlert className="text-amber-300" size={16} />
        </div>
        <div className="mt-3 space-y-2">
          {inspectionsQuery.data.map((item) => (
            <div key={item.id} className="rounded-xl border border-white/10 p-3">
              <p className="text-sm font-medium text-slate-100">{item.plate} • {item.model}</p>
              <p className="text-xs text-slate-400">Severity: {item.severity} | Risk score: {item.riskScore}</p>
            </div>
          ))}
        </div>
      </Card>

      <div className="sticky bottom-16 md:bottom-4">
        <Link href="/inspection/new"><Button className="w-full">Start New Inspection <ArrowRight size={16} className="ml-2" /></Button></Link>
      </div>
    </div>
  );
}
