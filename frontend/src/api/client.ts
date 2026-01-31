const ACCESS_TOKEN_KEY = "dc_access_token";
const REFRESH_TOKEN_KEY = "dc_refresh_token";
const TENANT_SLUG_KEY = "dc_tenant_slug";

const OPEN_PATH_PREFIXES = ["/api/auth/", "/api/docs", "/api/schema/"];
const OPEN_EXACT_PATHS = [
  "/api/tenants/",
  "/api/tenant/bootstrap/",
  "/api/invites/accept/",
  "/api/me/tenants/",
];

const isBrowser = () => typeof window !== "undefined";

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(tokens: { access: string; refresh: string }) {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
}

export function clearAuth() {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(TENANT_SLUG_KEY);
}

export function getTenantSlug(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(TENANT_SLUG_KEY);
}

export function setTenantSlug(slug: string) {
  if (!isBrowser()) return;
  window.localStorage.setItem(TENANT_SLUG_KEY, slug);
}

export function clearTenantSlug() {
  if (!isBrowser()) return;
  window.localStorage.removeItem(TENANT_SLUG_KEY);
}

function shouldAttachTenant(path: string) {
  if (!path.startsWith("/api/")) return false;
  if (OPEN_PATH_PREFIXES.some((prefix) => path.startsWith(prefix))) return false;
  if (OPEN_EXACT_PATHS.includes(path)) return false;
  return true;
}

function buildErrorMessage(data: unknown, fallback: string) {
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (typeof data === "object" && data !== null) {
    const detail = (data as { detail?: string }).detail;
    if (detail) return detail;
  }
  try {
    return JSON.stringify(data);
  } catch (err) {
    return fallback;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined && options.body !== null;

  if (hasBody && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (shouldAttachTenant(path)) {
    const tenantSlug = getTenantSlug();
    if (!tenantSlug) {
      throw new Error("Missing tenant selection.");
    }
    headers.set("X-Tenant", tenantSlug);
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    let data: unknown = null;
    let message = response.statusText || "Request failed";

    if (contentType.includes("application/json")) {
      data = await response.json();
      message = buildErrorMessage(data, message);
    } else {
      const text = await response.text();
      if (text) message = text;
    }

    const error = new Error(message) as Error & { status?: number; data?: unknown };
    error.status = response.status;
    error.data = data;
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}
