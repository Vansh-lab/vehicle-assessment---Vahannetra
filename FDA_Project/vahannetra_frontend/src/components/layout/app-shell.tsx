"use client";

import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { BarChart3, ClipboardList, Home, Settings, UserCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/components/providers/i18n-provider";

const links = [
  { href: "/dashboard", labelKey: "nav.dashboard", icon: Home },
  { href: "/inspection/new", labelKey: "nav.inspect", icon: ClipboardList },
  { href: "/history", labelKey: "nav.history", icon: UserCircle2 },
  { href: "/analytics", labelKey: "nav.analytics", icon: BarChart3 },
  { href: "/settings", labelKey: "nav.settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useLocation().pathname;
  const { locale, setLocale, t } = useI18n();

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl gap-4 px-4 pb-24 pt-4 md:px-6 md:pb-8">
      <aside className="hidden w-56 shrink-0 rounded-2xl border border-white/10 bg-slate-900/70 p-4 md:block">
        <p className="text-lg font-bold text-cyan-200">Vahannetra AI</p>
        <p className="mt-1 text-xs text-slate-400">{t("app.tagline", "Vehicle Damage Intelligence")}</p>
        <label className="mt-4 block text-xs text-slate-400" htmlFor="locale-selector">
          {t("locale.label", "Language")}
        </label>
        <select
          id="locale-selector"
          className="mt-1 w-full rounded-lg border border-white/20 bg-slate-950/70 px-2 py-1 text-xs text-slate-200"
          value={locale}
          onChange={(event) => setLocale(event.target.value === "hi" ? "hi" : "en")}
        >
          <option value="en">{t("locale.english", "English")}</option>
          <option value="hi">{t("locale.hindi", "Hindi")}</option>
        </select>
        <nav className="mt-6 space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                to={link.href}
                className={cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-sm",
                  active ? "bg-cyan-400/20 text-cyan-100" : "text-slate-300 hover:bg-white/10",
                )}
              >
                <Icon size={16} />
                {t(link.labelKey)}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main id="main-content" className="flex-1">{children}</main>
      <nav className="fixed inset-x-3 bottom-3 z-20 grid grid-cols-5 rounded-2xl border border-white/15 bg-slate-900/90 p-2 backdrop-blur md:hidden">
        {links.map((link) => {
          const Icon = link.icon;
          const active = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              to={link.href}
              className={cn(
                "flex flex-col items-center rounded-lg py-1 text-[11px]",
                active ? "text-cyan-200" : "text-slate-400",
              )}
            >
              <Icon size={16} />
              {t(link.labelKey)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
