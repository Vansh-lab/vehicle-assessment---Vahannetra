"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getAnalytics } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states/error-state";

export default function AnalyticsPage() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["analytics"], queryFn: getAnalytics });
  if (isLoading) return <Skeleton className="h-64" />;
  if (isError || !data) return <ErrorState message="Analytics unavailable." onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-lg font-semibold text-slate-100">Severity Trends</p>
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="month" stroke="#93a3be" />
              <YAxis stroke="#93a3be" />
              <Tooltip />
              <Bar dataKey="low" fill="#35d48d" radius={[6, 6, 0, 0]} />
              <Bar dataKey="medium" fill="#ffb648" radius={[6, 6, 0, 0]} />
              <Bar dataKey="high" fill="#ff5a7a" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card>
        <p className="text-lg font-semibold text-slate-100">Vehicle-wise Risk Ranking</p>
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.riskRanking}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="model" stroke="#93a3be" />
              <YAxis stroke="#93a3be" />
              <Tooltip />
              <Line type="monotone" dataKey="risk" stroke="#00e5ff" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
