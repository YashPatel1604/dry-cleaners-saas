import React, { useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  ClipboardList,
  CreditCard,
  Gauge,
  LayoutDashboard,
  Mail,
  ShieldCheck,
  Users,
  UserPlus,
  Settings,
} from "lucide-react";

import { cn } from "../../lib/utils";
import { useAuth } from "../../auth/AuthContext";
import { useTenant } from "../../tenant/TenantContext";
import { Button } from "../ui/button";

type NavItem = {
  to: string;
  label: string;
  icon: React.ElementType;
};

const NAV_SECTIONS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: "Work",
    items: [
      { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { to: "/orders", label: "Orders", icon: ClipboardList },
      { to: "/customers", label: "Customers", icon: Users },
      { to: "/inventory", label: "Inventory", icon: Boxes },
      { to: "/payments", label: "Payments", icon: CreditCard },
      { to: "/reports", label: "Reports", icon: BarChart3 },
      { to: "/queue", label: "Queue", icon: Gauge },
    ],
  },
  {
    title: "Admin",
    items: [
      { to: "/invites", label: "Invites", icon: Mail },
      { to: "/team", label: "Team", icon: UserPlus },
      { to: "/audit", label: "Audit", icon: ShieldCheck },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function NavSection({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div className="space-y-2">
      <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground/80">
        {title}
      </div>
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
                  "hover:bg-sidebar-accent hover:text-foreground",
                  isActive
                    ? "bg-sidebar-accent text-foreground shadow-sm"
                    : "text-muted-foreground"
                )
              }
            >
              <Icon size={18} />
              {item.label}
            </NavLink>
          );
        })}
      </div>
    </div>
  );
}

export default function AppShell(): JSX.Element {
  const { logout } = useAuth();
  const { tenantSlug, tenants } = useTenant();
  const location = useLocation();
  const navigate = useNavigate();

  const currentTenant = useMemo(() => {
    if (!tenantSlug) return null;
    return tenants.find((t) => t.tenant_slug === tenantSlug) ?? null;
  }, [tenantSlug, tenants]);

  const currentLabel = useMemo(() => {
    for (const section of NAV_SECTIONS) {
      for (const item of section.items) {
        if (location.pathname.startsWith(item.to)) {
          return item.label;
        }
      }
    }
    return "Console";
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex">
      <aside className="hidden lg:flex w-72 flex-col border-r border-sidebar-border bg-sidebar px-5 py-6">
        <div className="flex items-center gap-3 px-2">
          <div className="h-11 w-11 rounded-2xl bg-primary text-primary-foreground flex items-center justify-center text-lg font-semibold">
            DC
          </div>
          <div>
            <div className="text-sm uppercase tracking-[0.28em] text-muted-foreground">
              Dry Cleaners
            </div>
            <div className="text-lg font-semibold">Operations Console</div>
          </div>
        </div>

        <div className="mt-10 space-y-8">
          {NAV_SECTIONS.map((section) => (
            <NavSection key={section.title} title={section.title} items={section.items} />
          ))}
        </div>

        <div className="mt-auto pt-8 space-y-3">
          <div className="rounded-2xl border border-sidebar-border bg-white/70 px-4 py-3 text-sm text-muted-foreground">
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground/70">
              Active Tenant
            </div>
            <div className="mt-2 font-medium text-foreground">
              {currentTenant?.tenant_name || tenantSlug || "No tenant"}
            </div>
            {currentTenant?.tenant_slug && (
              <div className="text-xs">{currentTenant.tenant_slug}</div>
            )}
            {currentTenant?.role && (
              <div className="mt-1 text-xs text-muted-foreground">
                Role: {currentTenant.role}
              </div>
            )}
          </div>
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => navigate("/select-tenant")}
          >
            Switch tenant
          </Button>
          <Button variant="outline" className="w-full" onClick={() => logout()}>
            Log out
          </Button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-20 border-b border-border/70 bg-white/70 backdrop-blur">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-muted-foreground/70">
                {tenantSlug ? `Tenant ${tenantSlug}` : "Tenant not selected"}
              </div>
              <div className="text-2xl font-semibold">{currentLabel}</div>
            </div>
            <div className="hidden md:flex items-center gap-3">
              <Button variant="outline" onClick={() => navigate("/select-tenant")}>
                Switch tenant
              </Button>
              <Button onClick={() => logout()}>Log out</Button>
            </div>
          </div>
          <div className="px-6 pb-4 lg:hidden">
            <select
              className="h-10 w-full rounded-xl border border-input bg-white/80 px-3 text-sm"
              value={location.pathname}
              onChange={(e) => navigate(e.target.value)}
            >
              {NAV_SECTIONS.flatMap((section) =>
                section.items.map((item) => (
                  <option key={item.to} value={item.to}>
                    {item.label}
                  </option>
                ))
              )}
            </select>
          </div>
        </header>

        <main className="flex-1 px-6 py-6 page-enter">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
