"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "@/lib/api/services";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/states/error-state";

const pieColors = ["#00e5ff", "#35d48d", "#ffb648", "#ff5a7a", "#9f7aea"];

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
      const nextSize = { width: nextWidth, height: nextHeight };
      setSize((prev) => (hasSameSize(prev, nextSize) ? prev : nextSize));
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

function setupCanvas(canvas: HTMLCanvasElement, width: number, height: number) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return ctx;
}

function CanvasChart({
  size,
  draw,
}: {
  size: { width: number; height: number };
  draw: (ctx: CanvasRenderingContext2D, width: number, height: number) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || size.width <= 0 || size.height <= 0) return;
    const ctx = setupCanvas(canvas, size.width, size.height);
    if (!ctx) return;
    ctx.clearRect(0, 0, size.width, size.height);
    draw(ctx, size.width, size.height);
  }, [draw, size.height, size.width]);

  return <canvas ref={canvasRef} className="h-full w-full rounded-lg bg-slate-900/20" />;
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
          {({ width, height }) => {
            const maxY = Math.max(...data.trends.map((item) => item.low + item.medium + item.high), 1);
            return (
              <CanvasChart
                size={{ width, height }}
                draw={(ctx, chartWidth, chartHeight) => {
                  const margin = { top: 18, right: 16, bottom: 34, left: 40 };
                  const innerWidth = chartWidth - margin.left - margin.right;
                  const innerHeight = chartHeight - margin.top - margin.bottom;
                  const barGroupWidth = innerWidth / data.trends.length;
                  const barWidth = Math.max(8, barGroupWidth / 5);

                  ctx.strokeStyle = "rgba(255,255,255,0.15)";
                  ctx.lineWidth = 1;
                  ctx.beginPath();
                  ctx.moveTo(margin.left, margin.top);
                  ctx.lineTo(margin.left, chartHeight - margin.bottom);
                  ctx.lineTo(chartWidth - margin.right, chartHeight - margin.bottom);
                  ctx.stroke();

                  data.trends.forEach((row, index) => {
                    const xBase = margin.left + index * barGroupWidth + barGroupWidth / 2 - barWidth * 1.7;
                    const bars = [
                      { value: row.low, color: "#35d48d" },
                      { value: row.medium, color: "#ffb648" },
                      { value: row.high, color: "#ff5a7a" },
                    ];

                    bars.forEach((bar, barIndex) => {
                      const barHeight = (bar.value / maxY) * innerHeight;
                      const x = xBase + barIndex * (barWidth + 4);
                      const y = margin.top + innerHeight - barHeight;
                      ctx.fillStyle = bar.color;
                      ctx.fillRect(x, y, barWidth, barHeight);
                    });

                    ctx.fillStyle = "#93a3be";
                    ctx.font = "11px sans-serif";
                    ctx.textAlign = "center";
                    ctx.fillText(row.month, margin.left + index * barGroupWidth + barGroupWidth / 2, chartHeight - 12);
                  });
                }}
              />
            );
          }}
        </ChartCanvas>
      </Card>

      <Card>
        <p className="text-lg font-semibold text-slate-100">Damage Distribution</p>
        <ChartCanvas>
          {({ width, height }) => {
            const total = data.distribution.reduce((sum, item) => sum + item.count, 0) || 1;
            return (
              <CanvasChart
                size={{ width, height }}
                draw={(ctx, chartWidth, chartHeight) => {
                  const centerX = chartWidth * 0.35;
                  const centerY = chartHeight * 0.5;
                  const radius = Math.min(chartWidth, chartHeight) * 0.28;
                  let startAngle = -Math.PI / 2;

                  data.distribution.forEach((item, index) => {
                    const slice = (item.count / total) * Math.PI * 2;
                    ctx.beginPath();
                    ctx.moveTo(centerX, centerY);
                    ctx.arc(centerX, centerY, radius, startAngle, startAngle + slice);
                    ctx.closePath();
                    ctx.fillStyle = pieColors[index % pieColors.length];
                    ctx.fill();
                    startAngle += slice;
                  });

                  ctx.font = "12px sans-serif";
                  ctx.textAlign = "left";
                  data.distribution.forEach((item, index) => {
                    const y = 24 + index * 20;
                    const x = chartWidth * 0.65;
                    ctx.fillStyle = pieColors[index % pieColors.length];
                    ctx.fillRect(x, y - 10, 10, 10);
                    ctx.fillStyle = "#cbd5e1";
                    ctx.fillText(`${item.category} (${item.count})`, x + 16, y);
                  });
                }}
              />
            );
          }}
        </ChartCanvas>
      </Card>

      <Card>
        <p className="text-lg font-semibold text-slate-100">Vehicle-wise Risk Ranking</p>
        <ChartCanvas>
          {({ width, height }) => {
            const maxRisk = Math.max(...data.riskRanking.map((item) => item.risk), 1);
            return (
              <CanvasChart
                size={{ width, height }}
                draw={(ctx, chartWidth, chartHeight) => {
                  const margin = { top: 20, right: 20, bottom: 42, left: 40 };
                  const innerWidth = chartWidth - margin.left - margin.right;
                  const innerHeight = chartHeight - margin.top - margin.bottom;

                  ctx.strokeStyle = "rgba(255,255,255,0.15)";
                  ctx.lineWidth = 1;
                  ctx.beginPath();
                  ctx.moveTo(margin.left, margin.top);
                  ctx.lineTo(margin.left, chartHeight - margin.bottom);
                  ctx.lineTo(chartWidth - margin.right, chartHeight - margin.bottom);
                  ctx.stroke();

                  ctx.strokeStyle = "#00e5ff";
                  ctx.lineWidth = 2.5;
                  ctx.beginPath();
                  data.riskRanking.forEach((item, index) => {
                    const x =
                      margin.left +
                      (data.riskRanking.length === 1
                        ? innerWidth / 2
                        : (index / (data.riskRanking.length - 1)) * innerWidth);
                    const y = margin.top + innerHeight - (item.risk / maxRisk) * innerHeight;
                    if (index === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);
                  });
                  ctx.stroke();

                  ctx.fillStyle = "#93a3be";
                  ctx.font = "11px sans-serif";
                  ctx.textAlign = "center";
                  data.riskRanking.forEach((item, index) => {
                    const x =
                      margin.left +
                      (data.riskRanking.length === 1
                        ? innerWidth / 2
                        : (index / (data.riskRanking.length - 1)) * innerWidth);
                    ctx.fillText(item.model, x, chartHeight - 12);
                  });
                }}
              />
            );
          }}
        </ChartCanvas>
      </Card>
    </div>
  );
}
