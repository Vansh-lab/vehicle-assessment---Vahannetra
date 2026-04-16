import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-white/10 bg-slate-900/70 p-4 shadow-[0_10px_30px_rgba(2,12,32,0.5)] backdrop-blur",
        className,
      )}
      {...props}
    />
  );
}
