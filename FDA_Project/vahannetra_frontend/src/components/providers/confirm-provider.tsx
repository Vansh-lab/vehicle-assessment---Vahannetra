"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useI18n } from "@/components/providers/i18n-provider";

interface ConfirmOptions {
  title?: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

interface ConfirmContextValue {
  confirm: (options?: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

interface ConfirmState extends ConfirmOptions {
  open: boolean;
  resolve?: (accepted: boolean) => void;
}

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const [state, setState] = useState<ConfirmState>({ open: false });

  const close = useCallback((accepted: boolean) => {
    state.resolve?.(accepted);
    setState({ open: false });
  }, [state]);

  const confirm = useCallback((options?: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setState({
        open: true,
        resolve,
        title: options?.title,
        message: options?.message,
        confirmLabel: options?.confirmLabel,
        cancelLabel: options?.cancelLabel,
      });
    });
  }, []);

  const value = useMemo(() => ({ confirm }), [confirm]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {state.open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
          <Card className="w-full max-w-md space-y-3 border-white/20">
            <p className="text-lg font-semibold text-slate-100">{state.title ?? t("confirm.title")}</p>
            <p className="text-sm text-slate-300">{state.message ?? t("confirm.message")}</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => close(false)}>
                {state.cancelLabel ?? t("common.cancel")}
              </Button>
              <Button onClick={() => close(true)}>{state.confirmLabel ?? t("common.confirm")}</Button>
            </div>
          </Card>
        </div>
      ) : null}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const context = useContext(ConfirmContext);
  if (!context) throw new Error("useConfirm must be used within ConfirmProvider");
  return context;
}
