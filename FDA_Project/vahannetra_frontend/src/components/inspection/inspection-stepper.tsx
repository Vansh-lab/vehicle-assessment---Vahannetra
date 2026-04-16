import { cn } from "@/lib/utils";

export function InspectionStepper({ steps, activeStep }: { steps: string[]; activeStep: number }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {steps.map((step, index) => (
        <div key={step} className="space-y-1">
          <div
            className={cn(
              "h-1.5 rounded-full",
              index <= activeStep ? "bg-cyan-300" : "bg-white/10",
            )}
          />
          <p className={cn("text-[11px]", index <= activeStep ? "text-cyan-100" : "text-slate-500")}>
            {step}
          </p>
        </div>
      ))}
    </div>
  );
}
