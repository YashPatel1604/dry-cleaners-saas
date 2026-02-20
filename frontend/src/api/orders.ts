import { apiFetch } from "./client";

export type OrderCard = {
  order_id: number;
  pickup_id: string | null;
  order_sku?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  barcode_svg_url?: string;
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

export type StorageLocationLookup = {
  barcode: string;
  exists: boolean;
  rack_number: string | null;
};

export type StorageLocationAssignment = {
  order_id: number;
  order_sku: string;
  location_barcode: string | null;
  rack_number: string | null;
  assigned_at: string | null;
  location_created?: boolean;
  cleared_orders?: number;
};

export type StorageLocationStatusRow = {
  location_barcode: string;
  rack_number: string | null;
  occupied: boolean;
  current_order_id: number | null;
  current_order_sku: string | null;
  current_order_status: string | null;
  assigned_at: string | null;
};

export type StorageLocationStatusResponse = {
  count: number;
  results: StorageLocationStatusRow[];
};

export type StorageLocationHistoryEvent = {
  id: string;
  created_at: string | null;
  action: string;
  actor_type: string;
  actor_id: string;
  actor_label: string;
  request_id: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type StorageLocationHistoryResponse = {
  order_id: number;
  count: number;
  events: StorageLocationHistoryEvent[];
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

export async function lookupStorageLocation(barcode: string) {
  return apiFetch<StorageLocationLookup>(`/api/orders/storage-locations/lookup/`, {
    method: "POST",
    body: JSON.stringify({ barcode }),
  });
}

export async function fetchStorageLocationStatus(params?: {
  q?: string;
  occupied?: boolean;
}) {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set("q", params.q);
  if (params?.occupied !== undefined) {
    searchParams.set("occupied", params.occupied ? "true" : "false");
  }

  const query = searchParams.toString();
  const path = query
    ? `/api/orders/storage-locations/status/?${query}`
    : "/api/orders/storage-locations/status/";
  return apiFetch<StorageLocationStatusResponse>(path);
}

export async function assignStorageLocationByScan(input: {
  location_barcode: string;
  order_barcode: string;
  rack_number?: string;
  force_clear?: boolean;
}) {
  return apiFetch<StorageLocationAssignment>(`/api/orders/storage-locations/assign/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function fetchOrderStorageLocation(orderId: string | number) {
  return apiFetch<StorageLocationAssignment>(`/api/orders/${orderId}/storage-location/`);
}

export async function fetchOrderStorageLocationHistory(orderId: string | number) {
  return apiFetch<StorageLocationHistoryResponse>(
    `/api/orders/${orderId}/storage-location/history/`
  );
}

export async function clearOrderStorageLocation(orderId: string | number) {
  return apiFetch<StorageLocationAssignment>(`/api/orders/${orderId}/storage-location/clear/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
