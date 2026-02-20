import { apiFetch } from "./client";

export type OrderReceipt = {
  id: number;
  order_number?: number;
  order_sku?: string;
  barcode_svg_url?: string;
  status: string;
  due_at: string | null;
  notes?: string | null;
  created_at: string;
  settled_at?: string | null;
  customer: {
    id: number;
    name: string;
    phone?: string | null;
    email?: string | null;
  } | null;
  items: {
    id: number;
    item: number;
    item_name: string;
    quantity: number;
    unit_price_cents: number;
    line_total_cents: number;
  }[];
  payments: {
    id: number;
    method: string;
    status: string;
    direction: string;
    amount_cents: number;
    created_at: string;
  }[];
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  paid_cents: number;
  net_paid_cents: number;
  balance_due_cents: number;
  change_due_cents: number;
};

export async function fetchOrderReceipt(orderId: string | number) {
  return apiFetch<OrderReceipt>(`/api/orders/${orderId}/receipt/`);
}

export async function fetchOrderBarcodeSvg(orderId: string | number) {
  return apiFetch<string>(`/api/orders/${orderId}/barcode.svg/`);
}

export async function fetchOrderTimeline(orderId: string | number) {
  return apiFetch<any[]>(`/api/orders/${orderId}/timeline/`);
}

export async function fetchOrderNotes(orderId: string | number) {
  return apiFetch<any[]>(`/api/orders/${orderId}/notes/`);
}

export async function addOrderNote(orderId: string | number, note: string) {
  return apiFetch(`/api/orders/${orderId}/notes/`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function markOrderReady(orderId: string | number) {
  return apiFetch(`/api/orders/${orderId}/mark_ready/`, {
    method: "POST",
  });
}

export async function markOrderPickedUp(
  orderId: string | number,
  options?: { clear_location?: boolean }
) {
  return apiFetch(`/api/orders/${orderId}/pickup/`, {
    method: "POST",
    body: JSON.stringify(options ?? {}),
  });
}

export async function updateOrderStatus(
  orderId: string | number,
  status: string
) {
  return apiFetch(`/api/orders/${orderId}/`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function createPickupPayment(
  orderId: string | number,
  input: {
    amount_cents: number;
    method: "CASH" | "CARD" | "ONLINE" | "OTHER";
    reference?: string;
    note?: string;
  }
) {
  return apiFetch(`/api/orders/${orderId}/pickup-payment/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
