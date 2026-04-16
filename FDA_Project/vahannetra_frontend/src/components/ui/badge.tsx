import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-cyan-400/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-medium text-cyan-200",
        className,
      )}
      {...props}
    />
  );
}
