"use client";
import { LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const ROLE_LABEL: Record<string, string> = {
  INSPECTOR: "Inspector",
  SUPERVISOR: "Supervisor",
  ADMINISTRATOR: "Administrator",
};

export function Topbar({ title }: { title: string }) {
  const { user, logout } = useAuth();
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-line bg-white px-6">
      <h1 className="font-heading text-lg font-semibold text-ink-900">{title}</h1>
      <div className="flex items-center gap-3">
        {user && (
          <>
            <div className="text-right">
              <div className="text-sm font-medium text-ink-900">{user.full_name}</div>
              <Badge variant="outline" className="mt-0.5">
                {ROLE_LABEL[user.role] ?? user.role}
              </Badge>
            </div>
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
              <LogOut className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
