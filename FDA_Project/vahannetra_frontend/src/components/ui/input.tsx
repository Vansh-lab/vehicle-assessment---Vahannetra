import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-xl border border-white/15 bg-slate-950/70 px-3 text-sm text-white placeholder:text-slate-400 focus:border-cyan-300 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}
