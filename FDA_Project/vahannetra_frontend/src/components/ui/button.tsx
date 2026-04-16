import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
  {
    variants: {
      variant: {
        primary: "bg-cyan-400/90 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(0,229,255,0.35)]",
        secondary: "bg-white/10 text-white hover:bg-white/20 border border-white/15",
        ghost: "bg-transparent text-slate-200 hover:bg-white/10",
        danger: "bg-rose-500/90 text-white hover:bg-rose-400",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-11 px-4",
        lg: "h-12 px-5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
