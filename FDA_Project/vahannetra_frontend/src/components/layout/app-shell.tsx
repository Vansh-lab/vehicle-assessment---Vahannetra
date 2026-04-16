"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, ClipboardList, Home, Settings, UserCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/inspection/new", label: "Inspect", icon: ClipboardList },
  { href: "/history", label: "History", icon: UserCircle2 },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl gap-4 px-4 pb-24 pt-4 md:px-6 md:pb-8">
      <aside className="hidden w-56 shrink-0 rounded-2xl border border-white/10 bg-slate-900/70 p-4 md:block">
        <p className="text-lg font-bold text-cyan-200">Vahannetra AI</p>
        <p className="mt-1 text-xs text-slate-400">Vehicle Damage Intelligence</p>
        <nav className="mt-6 space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-sm",
                  active ? "bg-cyan-400/20 text-cyan-100" : "text-slate-300 hover:bg-white/10",
                )}
              >
                <Icon size={16} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1">{children}</main>
      <nav className="fixed inset-x-3 bottom-3 z-20 grid grid-cols-5 rounded-2xl border border-white/15 bg-slate-900/90 p-2 backdrop-blur md:hidden">
        {links.map((link) => {
          const Icon = link.icon;
          const active = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex flex-col items-center rounded-lg py-1 text-[11px]",
                active ? "text-cyan-200" : "text-slate-400",
              )}
            >
              <Icon size={16} />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
