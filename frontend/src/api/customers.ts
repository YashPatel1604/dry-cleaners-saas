import { apiFetch } from "./client";

export type Customer = {
  id: number;
  name: string;
  phone?: string | null;
  email?: string | null;
  created_at?: string;
};

export async function searchCustomers(query: string) {
  return apiFetch<Customer[]>(
    `/api/tenant/customers/search/?q=${encodeURIComponent(query)}`
  );
}

export async function fetchCustomers(params?: { limit?: number; offset?: number }) {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  const path = query ? `/api/tenant/customers/?${query}` : "/api/tenant/customers/";
  return apiFetch<Customer[]>(path);
}

export async function createCustomer(payload: {
  name: string;
  phone?: string | null;
  email?: string | null;
  notes?: string | null;
}) {
  return apiFetch<Customer>("/api/tenant/customers/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchCustomerDetail(id: string | number) {
  return apiFetch<Customer & { notes?: string | null }>(
    `/api/tenant/customers/${id}/`
  );
}

export async function updateCustomer(
  id: string | number,
  payload: { name: string; phone?: string | null; email?: string | null; notes?: string | null }
) {
  return apiFetch<Customer & { notes?: string | null }>(
    `/api/tenant/customers/${id}/`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchCustomerOrders(
  id: string | number,
  params?: { limit?: number; offset?: number }
) {
  const search = new URLSearchParams();
  if (params?.limit !== undefined) search.set("limit", String(params.limit));
  if (params?.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  const path = query
    ? `/api/tenant/customers/${id}/orders?${query}`
    : `/api/tenant/customers/${id}/orders`;
  return apiFetch<{
    count: number;
    limit: number;
    offset: number;
    results: Array<{
      id: number;
      status: string;
      created_at: string;
      due_at: string | null;
      subtotal_cents: number;
      tax_cents: number;
      total_cents: number;
      paid_cents: number;
      settled_at: string | null;
      notes?: string | null;
    }>;
  }>(path);
}
