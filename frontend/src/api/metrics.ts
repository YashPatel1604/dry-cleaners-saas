import { clientJson } from "./client";

export type DashboardMetrics = {
  totalInvoices: number | null;
  totalPieces: number | null;
  todaysDrop: number | null;
  todaysPickup: number | null;
};

type DashboardSummary = {
  orders_today: number;
  orders_value_today: string;
  collected_today: string;
};

function parseMoney(value?: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return null;
  return parsed;
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  try {
    const summary = await clientJson<DashboardSummary>("/api/dashboard/summary/");
    return {
      // TODO: wire total invoices + total pieces when endpoints are available.
      totalInvoices: null,
      totalPieces: null,
      todaysDrop: parseMoney(summary.orders_value_today),
      todaysPickup: parseMoney(summary.collected_today),
    };
  } catch {
    return {
      totalInvoices: null,
      totalPieces: null,
      todaysDrop: null,
      todaysPickup: null,
    };
  }
}
