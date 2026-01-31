import { apiFetch } from "./client";

export type PaymentDailySummary = {
  date: string;
  totals: {
    count: number;
    in_cents: number;
    out_cents: number;
    net_cents: number;
    voided_cents: number;
    voided_count: number;
  };
  by_method: Array<{
    method: string;
    count: number;
    in_cents: number;
    out_cents: number;
    net_cents: number;
    voided_cents: number;
    voided_count: number;
  }>;
};

export async function fetchPaymentsDailySummary(date?: string) {
  const search = new URLSearchParams();
  if (date) search.set("date", date);
  const query = search.toString();
  const path = query
    ? `/api/payments/daily-summary/?${query}`
    : "/api/payments/daily-summary/";
  return apiFetch<PaymentDailySummary>(path);
}
