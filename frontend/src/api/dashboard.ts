import { apiFetch } from "./client";

export type DashboardSummary = {
  orders_today: number;
  orders_value_today: string;
  collected_today: string;
  in_progress: number;
  ready: number;
  overdue: number;
};

export type OrderCardsResponse = {
  count: number;
  results: unknown[];
};

export async function fetchDashboardSummary() {
  return apiFetch<DashboardSummary>("/api/dashboard/summary/");
}

export async function fetchTotalInvoices() {
  const data = await apiFetch<OrderCardsResponse>("/api/orders/cards/?limit=1&offset=0");
  return data.count ?? 0;
}
