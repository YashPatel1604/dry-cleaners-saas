import { apiFetch, clearAuth, getTenantSlug, setAuthTokens, setTenantSlug } from "./client";

export type TenantSummary = {
  tenant_id: number;
  tenant_slug: string;
  tenant_name: string;
  role: string;
};

export type AuthTokens = {
  access: string;
  refresh: string;
};

export async function fetchTenants() {
  return apiFetch<TenantSummary[]>("/api/me/tenants/");
}

export async function login(username: string, password: string) {
  const tokens = await apiFetch<AuthTokens>("/api/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  setAuthTokens(tokens);

  const tenants = await fetchTenants();
  if (!tenants.length) {
    clearAuth();
    throw new Error("No active tenant found for this account.");
  }

  if (tenants.length === 1) {
    setTenantSlug(tenants[0].tenant_slug);
  }

  return tenants;
}

export async function ensureTenant() {
  const tenants = await fetchTenants();
  if (!tenants.length) {
    clearAuth();
    throw new Error("No active tenant found for this account.");
  }

  const existing = getTenantSlug();
  if (existing && tenants.some((t) => t.tenant_slug === existing)) {
    return tenants;
  }

  if (tenants.length === 1) {
    setTenantSlug(tenants[0].tenant_slug);
    return tenants;
  }

  return tenants;
}
