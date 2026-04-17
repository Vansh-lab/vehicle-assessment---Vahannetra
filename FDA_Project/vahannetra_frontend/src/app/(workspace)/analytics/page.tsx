"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from "recharts";
import { getAnalytics } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states/error-state";

const pieColors = ["#00e5ff", "#35d48d", "#ffb648", "#ff5a7a", "#9f7aea"];
const chartHeight = 256;

function hasSameSize(a: { width: number; height: number }, b: { width: number; height: number }) {
  return a.width === b.width && a.height === b.height;
}

function ChartCanvas({ children }: { children: (size: { width: number; height: number }) => ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = rootRef.current;
    if (!element) return;

    const syncSize = () => {
      const nextWidth = element.clientWidth;
      const nextHeight = element.clientHeight;
      setSize((prev) => (hasSameSize(prev, { width: nextWidth, height: nextHeight }) ? prev : { width: nextWidth, height: nextHeight }));
    };

    syncSize();
    const observer = new ResizeObserver(syncSize);
    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={rootRef} className="mt-4 h-64 min-w-0">
      {size.width > 0 && size.height > 0 ? children(size) : <Skeleton className="h-full w-full" />}
    </div>
  );
}

export default function AnalyticsPage() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["analytics"], queryFn: getAnalytics });
  if (isLoading) return <Skeleton className="h-64" />;
  if (isError || !data) return <ErrorState message="Analytics unavailable." onRetry={() => refetch()} />;

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-lg font-semibold text-slate-100">Severity Trends</p>
        <ChartCanvas>
          {({ width, height }) => (
            <BarChart width={width} height={height || chartHeight} data={data.trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="month" stroke="#93a3be" />
              <YAxis stroke="#93a3be" />
              <Tooltip />
              <Bar dataKey="low" fill="#35d48d" radius={[6, 6, 0, 0]} />
              <Bar dataKey="medium" fill="#ffb648" radius={[6, 6, 0, 0]} />
              <Bar dataKey="high" fill="#ff5a7a" radius={[6, 6, 0, 0]} />
            </BarChart>
          )}
        </ChartCanvas>
      </Card>

      <Card>
        <p className="text-lg font-semibold text-slate-100">Damage Distribution</p>
        <ChartCanvas>
          {({ width, height }) => (
            <PieChart width={width} height={height || chartHeight}>
              <Pie data={data.distribution} dataKey="count" nameKey="category" outerRadius={95} label>
                {data.distribution.map((entry, index) => (
                  <Cell key={entry.category} fill={pieColors[index % pieColors.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          )}
        </ChartCanvas>
      </Card>

      <Card>
        <p className="text-lg font-semibold text-slate-100">Vehicle-wise Risk Ranking</p>
        <ChartCanvas>
          {({ width, height }) => (
            <LineChart width={width} height={height || chartHeight} data={data.riskRanking}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="model" stroke="#93a3be" />
              <YAxis stroke="#93a3be" />
              <Tooltip />
              <Line type="monotone" dataKey="risk" stroke="#00e5ff" strokeWidth={3} />
            </LineChart>
          )}
        </ChartCanvas>
      </Card>
    </div>
  );
}
