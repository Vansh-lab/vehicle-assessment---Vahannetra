import { cn } from "@/lib/utils";

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: string;
}

export function Switch({ checked, onCheckedChange, label }: SwitchProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "relative h-7 w-12 rounded-full border transition",
        checked ? "border-cyan-300 bg-cyan-400/40" : "border-white/20 bg-white/10",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full bg-white transition",
          checked ? "left-6" : "left-1",
        )}
      />
    </button>
  );
}
