type ApiFetchInit = RequestInit & { tenant?: boolean };

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  body: any;

  constructor(status: number, body: any, message?: string) {
    super(message ?? `Request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem("access_token");
  } catch {
    return null;
  }
}

export function getTenantSlug(): string | null {
  try {
    return localStorage.getItem("tenant_slug");
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem("access_token", token);
    } else {
      localStorage.removeItem("access_token");
    }
  } catch {
    // ignore storage errors
  }
}

export function setTenantSlug(slug: string | null): void {
  try {
    if (slug) {
      localStorage.setItem("tenant_slug", slug);
    } else {
      localStorage.removeItem("tenant_slug");
    }
  } catch {
    // ignore storage errors
  }
}

export function debugAuthHeaders(tenantOpt?: boolean): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (tenantOpt !== false) {
    const tenantSlug = getTenantSlug();
    if (tenantSlug) {
      headers["X-Tenant"] = tenantSlug;
    }
  }
  headers.Accept = "application/json";
  return headers;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object") return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE) return normalized;
  return `${API_BASE.replace(/\/$/, "")}${normalized}`;
}

function withAuthAndTenantHeaders(headers: Headers, tenantOpt?: boolean): void {
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (tenantOpt !== false) {
    const tenantSlug = getTenantSlug();
    if (tenantSlug) {
      headers.set("X-Tenant", tenantSlug);
    }
  }

  headers.set("Accept", "application/json");
}

export async function apiFetch(path: string, init: ApiFetchInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const tenantOpt = init.tenant;

  let body = init.body as any;
  const hasContentType = headers.has("Content-Type");

  if (body && isPlainObject(body) && !hasContentType) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  withAuthAndTenantHeaders(headers, tenantOpt);

  const response = await fetch(buildUrl(path), {
    ...init,
    headers,
    body,
  });

  return response;
}

export async function apiJson<T>(path: string, init: ApiFetchInit = {}): Promise<T> {
  const response = await apiFetch(path, init);

  let parsedBody: any = null;
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    try {
      parsedBody = await response.json();
    } catch {
      parsedBody = null;
    }
  } else {
    try {
      parsedBody = await response.text();
    } catch {
      parsedBody = null;
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("auth:unauthorized"));
    } else if (response.status === 403) {
      window.dispatchEvent(new Event("auth:forbidden"));
    }
    throw new ApiError(response.status, parsedBody);
  }

  return parsedBody as T;
}
