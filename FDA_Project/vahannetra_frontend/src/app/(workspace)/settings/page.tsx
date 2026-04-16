"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, MoonStar, Sun } from "lucide-react";
import { backendCapabilities } from "@/lib/api/backend-gaps";
import { getNotificationPreferences } from "@/lib/api/services";
import { useTheme } from "@/components/providers/theme-provider";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const { data, isLoading } = useQuery({ queryKey: ["notification-prefs"], queryFn: getNotificationPreferences });

  return (
    <div className="space-y-4">
      <Card>
        <p className="flex items-center gap-2 text-lg font-semibold text-slate-100"><Building2 size={18} /> Organization Info</p>
        <p className="mt-2 text-sm text-slate-300">Acme Claims Pvt Ltd • Mumbai Region • 42 active inspectors</p>
      </Card>

      <Card className="space-y-3">
        <p className="text-sm font-semibold text-slate-100">Notification Preferences</p>
        {isLoading || !data ? <Skeleton className="h-16" /> : (
          <div className="space-y-3">
            <div className="flex items-center justify-between"><p className="text-sm text-slate-300">Push notifications</p><Switch checked={data.push} onCheckedChange={() => undefined} label="push-preference" /></div>
            <div className="flex items-center justify-between"><p className="text-sm text-slate-300">Email notifications</p><Switch checked={data.email} onCheckedChange={() => undefined} label="email-preference" /></div>
            <div className="flex items-center justify-between"><p className="text-sm text-slate-300">Critical alerts only</p><Switch checked={data.criticalOnly} onCheckedChange={() => undefined} label="critical-only" /></div>
          </div>
        )}
      </Card>

      <Card className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">Theme</p>
          <p className="text-xs text-slate-400">Dark neon / Light mode</p>
        </div>
        <button type="button" className="flex items-center gap-2 rounded-xl border border-white/15 px-3 py-2 text-sm" onClick={toggleTheme}>
          {theme === "dark" ? <Sun size={16} /> : <MoonStar size={16} />} {theme === "dark" ? "Light" : "Dark"}
        </button>
      </Card>

      <Card>
        <p className="text-sm font-semibold text-slate-100">Backend Integration Status</p>
        <div className="mt-3 space-y-2">
          {backendCapabilities.map((item) => (
            <div key={item.key} className="rounded-xl border border-white/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm text-slate-200">{item.key}</p>
                <Badge className={item.status === "implemented" ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-200" : "border-amber-300/20 bg-amber-400/10 text-amber-100"}>{item.status}</Badge>
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
