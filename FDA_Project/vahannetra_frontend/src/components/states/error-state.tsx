import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card className="text-center py-10 border-rose-400/40">
      <AlertTriangle className="mx-auto mb-3 text-rose-300" />
      <p className="text-lg font-semibold text-slate-100">Something went wrong</p>
      <p className="mt-1 text-sm text-slate-400">{message}</p>
      {onRetry ? (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </Card>
  );
}
