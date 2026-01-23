import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { useTenant } from "../tenant/TenantContext";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";

export default function SelectTenant(): JSX.Element {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { tenants, reloadTenants, setTenantSlug } = useTenant();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    reloadTenants()
      .catch(() => {
        // ignore, UI will show empty state
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadTenants]);

  const onSelect = (slug: string) => {
    setTenantSlug(slug);
    navigate("/dashboard", { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <Card className="w-full max-w-lg glass-panel border-border/70">
        <CardContent className="p-6 space-y-5">
          <div>
            <div className="text-xs uppercase tracking-[0.35em] text-muted-foreground/70">
              Tenant selector
            </div>
            <h1 className="text-3xl font-semibold">Choose your location</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Select the store you want to manage.
            </p>
          </div>

          {loading ? (
            <div className="text-sm text-muted-foreground">Loading tenants...</div>
          ) : tenants.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              You have no tenant memberships. Ask an owner to invite you or bootstrap a tenant.
            </div>
          ) : (
            <div className="space-y-3">
              {tenants.map((tenant) => (
                <button
                  key={tenant.tenant_id}
                  type="button"
                  onClick={() => onSelect(tenant.tenant_slug)}
                  className="w-full rounded-xl border border-border bg-white/70 p-4 text-left transition hover:bg-white"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{tenant.tenant_name}</div>
                      <div className="text-xs text-muted-foreground">{tenant.tenant_slug}</div>
                    </div>
                    <div className="text-xs font-medium text-muted-foreground">
                      {tenant.role}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="pt-2">
            <Button variant="secondary" onClick={logout} className="w-full">
              Log out
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
