"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, MoonStar, Sun } from "lucide-react";
import { backendCapabilities } from "@/lib/api/backend-gaps";
import { getSettings, updateSettings } from "@/lib/api/services";
import { useTheme } from "@/components/providers/theme-provider";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/components/providers/i18n-provider";

type PrefKey = "push" | "email" | "critical_only";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { theme, toggleTheme, setTheme } = useTheme();
  const { locale, setLocale, t } = useI18n();
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const mutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings"], updated);
      queryClient.invalidateQueries({ queryKey: ["notification-prefs"] });
      setTheme(updated.theme);
    },
  });

  const toggleNotification = (key: PrefKey) => {
    if (!data) return;
    mutation.mutate({
      notifications: {
        push: key === "push" ? !data.notifications.push : data.notifications.push,
        email: key === "email" ? !data.notifications.email : data.notifications.email,
        criticalOnly: key === "critical_only" ? !data.notifications.critical_only : data.notifications.critical_only,
      },
    });
  };

  const toggleAppTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    toggleTheme();
    mutation.mutate({ theme: nextTheme });
  };

  return (
    <div className="space-y-4">
      <Card>
        <p className="flex items-center gap-2 text-lg font-semibold text-slate-100">
          <Building2 size={18} /> Organization Info
        </p>
        <p className="mt-2 text-sm text-slate-300">
          {data?.organization.name ?? "Acme Claims Pvt Ltd"} • {data?.organization.region ?? "Mumbai"} Region • {data?.organization.active_inspectors ?? 42} active inspectors
        </p>
      </Card>

      <Card className="space-y-3">
        <p className="text-sm font-semibold text-slate-100">Notification Preferences</p>
        {isLoading || !data ? (
          <Skeleton className="h-16" />
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-300">Push notifications</p>
              <Switch checked={data.notifications.push} onCheckedChange={() => toggleNotification("push")} label="push-preference" />
            </div>
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-300">Email notifications</p>
              <Switch checked={data.notifications.email} onCheckedChange={() => toggleNotification("email")} label="email-preference" />
            </div>
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-300">Critical alerts only</p>
              <Switch checked={data.notifications.critical_only} onCheckedChange={() => toggleNotification("critical_only")} label="critical-only" />
            </div>
          </div>
        )}
      </Card>

      <Card className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">Theme</p>
          <p className="text-xs text-slate-400">Dark neon / Light mode</p>
        </div>
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl border border-white/15 px-3 py-2 text-sm"
          onClick={toggleAppTheme}
        >
          {theme === "dark" ? <Sun size={16} /> : <MoonStar size={16} />} {theme === "dark" ? "Light" : "Dark"}
        </button>
      </Card>

      <Card className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">{t("locale.label", "Language")}</p>
          <p className="text-xs text-slate-400">UI localization preference</p>
        </div>
        <select
          className="rounded-xl border border-white/15 bg-slate-950/70 px-3 py-2 text-sm text-slate-100"
          value={locale}
          onChange={(event) => setLocale(event.target.value === "hi" ? "hi" : "en")}
        >
          <option value="en">{t("locale.english", "English")}</option>
          <option value="hi">{t("locale.hindi", "Hindi")}</option>
        </select>
      </Card>

      <Card>
        <p className="text-sm font-semibold text-slate-100">Backend Integration Status</p>
        <div className="mt-3 space-y-2">
          {backendCapabilities.map((item) => (
            <div key={item.key} className="rounded-xl border border-white/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-slate-200">{item.key}</p>
                <Badge
                  className={
                    item.status === "implemented"
                      ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-200"
                      : "border-amber-300/20 bg-amber-400/10 text-amber-100"
                  }
                >
                  {item.status}
                </Badge>
              </div>
              {item.endpoint ? <p className="mt-1 text-xs text-slate-400">{item.endpoint}</p> : null}
              {item.howToBuild ? <p className="mt-1 text-xs text-slate-400">How to build: {item.howToBuild}</p> : null}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
