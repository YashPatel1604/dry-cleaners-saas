import { apiFetch } from "./client";

export type WorkloadReport = {
  date: string;
  counts: {
    orders_due_today: number;
    orders_overdue: number;
    orders_ready_unpaid: number;
    orders_completed_unpicked: number;
  };
  avg_age_hours: {
    orders_due_today: number;
    orders_overdue: number;
    orders_ready_unpaid: number;
    orders_completed_unpicked: number;
  };
};

export type TopCustomer = {
  customer: {
    id: number;
    name: string;
    phone?: string | null;
  };
  orders_count: number;
  settled_total_cents: number;
  last_seen_at: string | null;
};

export type TopCustomersResponse = {
  start: string;
  end: string;
  results: TopCustomer[];
};

export type ReportItemSummary = {
  item_id: number;
  item__name: string;
  quantity: number;
  revenue_cents: number;
};

export type DailyCashCloseReport = {
  date: string;
  cash: { in_cents: number; out_cents: number; net_cents: number };
  card: { in_cents: number; out_cents: number; net_cents: number };
  adjustments: { in_cents: number; out_cents: number; net_cents: number };
  settlement: {
    orders_settled_count: number;
    settled_total_cents: number;
    settled_paid_cents: number;
    settled_change_cents: number;
    settled_balance_due_cents: number;
  };
};

export type OpsSummaryReport = {
  date: string;
  counts: {
    orders_due_today: number;
    orders_overdue: number;
    orders_ready: number;
    orders_ready_unpaid: number;
    orders_completed_unpicked: number;
    orders_picked_up_today: number;
    orders_settled_today: number;
  };
};

export type RevenueReport = {
  start: string;
  end: string;
  totals: {
    orders_settled_count: number;
    settled_total_cents: number;
    avg_order_value_cents: number;
    cash_net_cents: number;
    card_net_cents: number;
  };
  days: Array<{
    date: string;
    orders_settled_count: number;
    settled_total_cents: number;
    avg_order_value_cents: number;
    cash_net_cents: number;
    card_net_cents: number;
  }>;
};

export async function fetchWorkloadReport(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiFetch<WorkloadReport>(`/api/reports/workload/${query}`);
}

export async function fetchDailyCashClose(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiFetch<DailyCashCloseReport>(`/api/reports/daily-cash-close/${query}`);
}

export async function fetchOpsSummary(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiFetch<OpsSummaryReport>(`/api/reports/ops-summary/${query}`);
}

export async function fetchRevenueReport(input: { start: string; end: string }) {
  const params = new URLSearchParams({ start: input.start, end: input.end });
  return apiFetch<RevenueReport>(`/api/reports/revenue/?${params}`);
}

export async function fetchDailyCashCloseCsv(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiFetch<string>(`/api/reports/daily-cash-close.csv${query}`);
}

export async function fetchTopCustomers(input: {
  start: string;
  end: string;
  limit?: number;
}) {
  const params = new URLSearchParams({
    start: input.start,
    end: input.end,
  });
  if (input.limit) params.set("limit", String(input.limit));
  return apiFetch<TopCustomersResponse>(`/api/reports/customers/top/?${params}`);
}

export async function fetchTopItems(input: {
  start: string;
  end: string;
  limit?: number;
}) {
  const data = await apiFetch<{
    items?: { by_item?: ReportItemSummary[] };
  }>("/api/reports/query/", {
    method: "POST",
    body: JSON.stringify({
      date_start: input.start,
      date_end: input.end,
    }),
  });
  const items = data.items?.by_item ?? [];
  if (input.limit) return items.slice(0, input.limit);
  return items;
}
