import { apiFetch } from "./client";

export type DashboardSummary = {
  orders_today: number;
  pieces_today: number;
  orders_value_today: string;
  collected_today: string;
  orders_value_change_pct?: number | null;
  collected_change_pct?: number | null;
  in_progress: number;
  ready: number;
  overdue: number;
};

export type OrdersByStatusRow = {
  status: string;
  count: number;
};

export async function fetchDashboardSummary() {
  return apiFetch<DashboardSummary>("/api/dashboard/summary/");
}

export async function fetchTotalInvoices() {
  const data = await fetchDashboardSummary();
  return data.orders_today ?? 0;
}

export async function fetchOrdersByStatus() {
  return apiFetch<OrdersByStatusRow[]>("/api/dashboard/orders-by-status/");
}
