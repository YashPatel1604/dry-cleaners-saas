import React, { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  ClipboardList,
  Menu,
  Plus,
  Settings,
} from "lucide-react";

import { cn } from "../../lib/utils";
import { Dialog, DialogContent, DialogTrigger } from "../ui/dialog";
import { Button } from "../ui/button";

type NavItem = {
  to: string;
  label: string;
  icon: React.ElementType;
  matchPaths?: string[];
};

const NAV_ITEMS: NavItem[] = [
  { to: "/orders", label: "Orders", icon: ClipboardList, matchPaths: ["/orders"] },
  {
    to: "/extras",
    label: "Extras",
    icon: Plus,
    matchPaths: ["/extras", "/inventory", "/reports", "/queue"],
  },
  {
    to: "/admin",
    label: "Admin",
    icon: Settings,
    matchPaths: ["/admin", "/settings", "/team", "/invites", "/audit"],
  },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();

  return (
    <div className="flex h-full flex-col">
      <nav className="space-y-6">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              aria-current={
                item.matchPaths?.some((path) => location.pathname.startsWith(path))
                  ? "page"
                  : undefined
              }
              className={({ isActive }) => {
                const isCurrent =
                  isActive || item.matchPaths?.some((path) => location.pathname.startsWith(path));
                return cn(
                  "flex items-center gap-4 text-sm font-semibold uppercase tracking-[0.22em] transition",
                  isCurrent
                    ? "text-slate-900"
                    : "text-slate-500 hover:text-slate-900"
                );
              }}
            >
              <Icon size={20} className="text-current" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

export default function AppShell(): JSX.Element {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isHomeActive = useMemo(() => {
    return (
      location.pathname === "/" ||
      location.pathname.startsWith("/home") ||
      location.pathname.startsWith("/dashboard")
    );
  }, [location.pathname]);

  const isDropActive = useMemo(() => {
    return location.pathname.startsWith("/drop") || location.pathname.startsWith("/register");
  }, [location.pathname]);

  return (
    <div className="min-h-screen w-full bg-[#f7f8fb] text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
              <DialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="lg:hidden"
                  aria-label="Open navigation"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              </DialogTrigger>
              <DialogContent className="left-0 top-0 h-full w-[85vw] max-w-xs translate-x-0 translate-y-0 rounded-none border-r bg-white p-6 sm:rounded-none">
                <SidebarContent onNavigate={() => setMobileOpen(false)} />
              </DialogContent>
            </Dialog>
            <NavLink
              to="/drop"
              className={cn(
                "hidden text-sm font-semibold uppercase tracking-[0.34em] sm:inline-flex",
                isDropActive ? "text-slate-900" : "text-slate-500"
              )}
            >
              Drop
            </NavLink>
          </div>
          <NavLink
            to="/home"
            className={cn(
              "rounded-lg px-8 py-2.5 text-sm font-semibold uppercase tracking-[0.35em]",
              isHomeActive
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-900"
            )}
          >
            Home
          </NavLink>
          <div className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-500">
            Dashboard
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-70px)] w-full max-w-[1200px]">
        <aside className="hidden w-64 border-r border-slate-200 bg-white px-6 py-10 lg:flex">
          <SidebarContent />
        </aside>

        <main className="flex-1 px-6 py-10 page-enter lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
