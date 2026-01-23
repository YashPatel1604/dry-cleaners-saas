import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";

type Tenant = {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  collects_tax: boolean;
  tax_rate_bps: number;
};

export default function Settings(): JSX.Element {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiJson<Tenant>("/api/tenant/me/")
      .then((data) => setTenant(data))
      .catch(() => setError("Unable to load tenant settings"));
  }, []);

  const saveSettings = async () => {
    if (!tenant) return;
    setSaving(true);
    setError(null);
    try {
      const resp = await apiJson<{
        tenant: { id: number; slug: string };
        collects_tax: boolean;
        tax_rate_bps: number;
      }>("/api/tenant/settings/", {
        method: "PATCH",
        body: {
          collects_tax: tenant.collects_tax,
          tax_rate_bps: tenant.tax_rate_bps,
        },
      });
      setTenant({ ...tenant, collects_tax: resp.collects_tax, tax_rate_bps: resp.tax_rate_bps });
    } catch {
      setError("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const deactivateTenant = async () => {
    const confirmed = window.confirm(
      "Deactivate this tenant? All access will be blocked until reactivated manually."
    );
    if (!confirmed) return;
    await apiJson("/api/tenant/deactivate/", { method: "POST" });
    setTenant((prev) => (prev ? { ...prev, is_active: false } : prev));
  };

  if (!tenant) {
    return (
      <Card>
        <CardContent className="p-6">{error || "Loading settings..."}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Settings
        </div>
        <h1 className="text-3xl font-semibold">{tenant.name}</h1>
        <p className="text-sm text-muted-foreground">Tenant slug: {tenant.slug}</p>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Tax settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium">Collect tax</label>
            <input
              type="checkbox"
              checked={tenant.collects_tax}
              onChange={(e) => setTenant({ ...tenant, collects_tax: e.target.checked })}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Tax rate (bps)</label>
            <Input
              value={tenant.tax_rate_bps}
              onChange={(e) => setTenant({ ...tenant, tax_rate_bps: Number(e.target.value) })}
            />
          </div>
          <Button onClick={saveSettings} disabled={saving}>
            {saving ? "Saving..." : "Save settings"}
          </Button>
        </CardContent>
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Tenant status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>Status: {tenant.is_active ? "Active" : "Deactivated"}</div>
          <Button variant="outline" onClick={deactivateTenant} disabled={!tenant.is_active}>
            Deactivate tenant
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
