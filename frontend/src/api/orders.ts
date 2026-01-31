import { apiFetch } from "./client";

export type OrderCard = {
  order_id: number;
  pickup_id: string | null;
  status: string;
  created_at: string;
  updated_at?: string;
  customer?: {
    id: number;
    name: string;
    phone?: string | null;
    email?: string | null;
  } | null;
  money?: {
    total_cents?: number;
    net_paid_cents?: number;
    balance_due_cents?: number;
    change_due_cents?: number;
  };
};

export type OrderCardsResponse = {
  count: number;
  results: OrderCard[];
};

export async function fetchOrderCards(params?: {
  q?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set("q", params.q);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const path = query ? `/api/orders/cards/?${query}` : "/api/orders/cards/";
  return apiFetch<OrderCardsResponse>(path);
}

export async function createOrder(input: {
  customer: number;
  due_at?: string | null;
  notes?: string;
}) {
  return apiFetch(`/api/orders/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function createDropoffOrder(input: {
  customer: number;
  due_at?: string | null;
  notes?: string;
  initial_payment?: {
    amount_cents: number;
    method: "CASH" | "CARD" | "ONLINE" | "OTHER";
    reference?: string;
    note?: string;
  };
}) {
  return apiFetch(`/api/orders/dropoff/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function createOrderItem(input: {
  order: number;
  item: number;
  quantity: number;
}) {
  return apiFetch(`/api/order-items/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateOrderItem(
  orderItemId: string | number,
  input: { quantity?: number }
) {
  return apiFetch(`/api/order-items/${orderItemId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteOrderItem(orderItemId: string | number) {
  return apiFetch(`/api/order-items/${orderItemId}/`, {
    method: "DELETE",
  });
}
