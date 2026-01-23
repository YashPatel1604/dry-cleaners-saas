import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiJson, getTenantSlug, setTenantSlug as setTenantSlugStorage } from "../lib/api";
import { useAuth } from "../auth/AuthContext";

export type TenantInfo = {
  tenant_id: number;
  tenant_slug: string;
  tenant_name: string;
  role: "OWNER_ADMIN" | "OPERATOR";
};

export type TenantContextValue = {
  tenantSlug: string | null;
  setTenantSlug: (slug: string | null) => void;
  tenants: TenantInfo[];
  reloadTenants: () => Promise<void>;
};

const TenantContext = createContext<TenantContextValue | undefined>(undefined);

export function TenantProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const { token } = useAuth();
  const [tenantSlug, setTenantSlugState] = useState<string | null>(() => getTenantSlug());
  const [tenants, setTenants] = useState<TenantInfo[]>([]);

  const setTenantSlug = useCallback((slug: string | null) => {
    setTenantSlugStorage(slug);
    setTenantSlugState(slug);
  }, []);

  const reloadTenants = useCallback(async () => {
    const data = await apiJson<TenantInfo[]>("/api/me/tenants/", { tenant: false });
    setTenants(data || []);
  }, []);

  useEffect(() => {
    if (!token) {
      setTenantSlug(null);
      setTenants([]);
    }
  }, [token, setTenantSlug]);

  const value = useMemo<TenantContextValue>(
    () => ({ tenantSlug, setTenantSlug, tenants, reloadTenants }),
    [tenantSlug, setTenantSlug, tenants, reloadTenants]
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error("useTenant must be used within TenantProvider");
  }
  return ctx;
}
