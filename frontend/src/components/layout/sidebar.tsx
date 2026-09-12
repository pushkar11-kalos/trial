"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardPlus,
  FolderSearch,
  ShieldCheck,
  History,
  ScrollText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: null },
  { href: "/inspections/new", label: "New Inspection", icon: ClipboardPlus, roles: null },
  { href: "/repository", label: "Repository", icon: FolderSearch, roles: null },
  { href: "/audit", label: "Audit Trail", icon: History, roles: null },
  { href: "/admin/rules", label: "Rule Pack", icon: ShieldCheck, roles: ["ADMINISTRATOR", "SUPERVISOR"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-navy-900 text-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <ScrollText className="h-5 w-5 text-accent" />
        <div>
          <div className="font-heading text-sm font-bold leading-none tracking-tight">MetraCheck</div>
          <div className="mt-1 text-[10px] uppercase tracking-wider text-white/40">
            Legal Metrology
          </div>
        </div>
      </div>

      <nav className="mt-4 flex flex-1 flex-col gap-0.5 px-3">
        {NAV.filter((item) => !item.roles || item.roles.includes(user?.role ?? "")).map((item) => {
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-navy-700 text-white" : "text-white/60 hover:bg-navy-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-4 py-3 text-[11px] text-white/40">
        Prototype rule pack — verify against active official legal instruments
        before operational enforcement.
      </div>
    </aside>
  );
}
