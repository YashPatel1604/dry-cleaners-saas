import { apiFetch, apiJson, debugAuthHeaders, type ApiError } from "../lib/api";

export type ApiInit = Parameters<typeof apiFetch>[1];

export { ApiError };

export function clientFetch(path: string, init: ApiInit = {}) {
  return apiFetch(path, init);
}

export function clientJson<T>(path: string, init: ApiInit = {}) {
  return apiJson<T>(path, init);
}

export function authHeaders(includeTenant = true): Record<string, string> {
  return debugAuthHeaders(includeTenant);
}
