import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";

import {
  fetchDailyCashClose,
  fetchDailyCashCloseCsv,
  fetchOpsSummary,
  fetchRevenueReport,
  fetchTopCustomers,
  fetchTopItems,
  fetchWorkloadReport,
  type DailyCashCloseReport,
  type OpsSummaryReport,
  type RevenueReport,
  type ReportItemSummary,
  type TopCustomer,
  type WorkloadReport,
} from "@/api/reports";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const toDateInput = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const formatCurrency = (cents: number | null | undefined) => {
  const safe = Number(cents ?? 0);
  return `$${(safe / 100).toFixed(2)}`;
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
};

export function DefaultReportsPage() {
  const [date, setDate] = useState(() => toDateInput(new Date()));
  const [range, setRange] = useState<"7d" | "30d">("7d");
  const [dailyCashClose, setDailyCashClose] = useState<DailyCashCloseReport | null>(
    null
  );
  const [opsSummary, setOpsSummary] = useState<OpsSummaryReport | null>(null);
  const [workload, setWorkload] = useState<WorkloadReport | null>(null);
  const [revenueReport, setRevenueReport] = useState<RevenueReport | null>(null);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [topItems, setTopItems] = useState<ReportItemSummary[]>([]);
  const [dailyLoading, setDailyLoading] = useState(true);
  const [dailyError, setDailyError] = useState<string | null>(null);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [rangeLoading, setRangeLoading] = useState(true);
  const [rangeError, setRangeError] = useState<string | null>(null);

  const rangeDates = useMemo(() => {
    const end = new Date(date);
    const days = range === "7d" ? 6 : 29;
    const start = new Date(end);
    start.setDate(end.getDate() - days);
    return {
      start: toDateInput(start),
      end: toDateInput(end),
    };
  }, [date, range]);

  useEffect(() => {
    let isMounted = true;
    const loadDaily = async () => {
      setDailyLoading(true);
      setDailyError(null);
      try {
        const [cashClose, ops, workloadRes] = await Promise.all([
          fetchDailyCashClose(date),
          fetchOpsSummary(date),
          fetchWorkloadReport(date),
        ]);
        if (!isMounted) return;
        setDailyCashClose(cashClose);
        setOpsSummary(ops);
        setWorkload(workloadRes);
      } catch (err) {
        if (!isMounted) return;
        setDailyError(
          err instanceof Error ? err.message : "Unable to load daily reports."
        );
      } finally {
        if (isMounted) setDailyLoading(false);
      }
    };

    loadDaily();
    return () => {
      isMounted = false;
    };
  }, [date]);

  useEffect(() => {
    let isMounted = true;
    const loadRange = async () => {
      setRangeLoading(true);
      setRangeError(null);
      try {
        const [revenue, customers, items] = await Promise.all([
          fetchRevenueReport({
            start: rangeDates.start,
            end: rangeDates.end,
          }),
          fetchTopCustomers({
            start: rangeDates.start,
            end: rangeDates.end,
            limit: 5,
          }),
          fetchTopItems({
            start: rangeDates.start,
            end: rangeDates.end,
            limit: 5,
          }),
        ]);
        if (!isMounted) return;
        setRevenueReport(revenue);
        setTopCustomers(customers.results || []);
        setTopItems(items || []);
      } catch (err) {
        if (!isMounted) return;
        setRangeError(
          err instanceof Error ? err.message : "Unable to load range reports."
        );
      } finally {
        if (isMounted) setRangeLoading(false);
      }
    };

    loadRange();
    return () => {
      isMounted = false;
    };
  }, [rangeDates]);

  const handleDownloadCsv = async () => {
    setDownloadLoading(true);
    setDailyError(null);
    try {
      const csv = await fetchDailyCashCloseCsv(date);
      const blob = new Blob([csv], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `daily-cash-close-${date}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setDailyError(
        err instanceof Error ? err.message : "Unable to download cash close CSV."
      );
    } finally {
      setDownloadLoading(false);
    }
  };

  return (
    <div className="max-w-6xl space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl text-gray-900">Reports</h1>
          <p className="text-sm text-gray-500">
            Daily operational reports and quick summaries.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">
            Date
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              className="ml-2 rounded-md border border-gray-300 px-2 py-1 text-sm"
            />
          </label>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadCsv}
            disabled={downloadLoading}
          >
            <Download className="h-4 w-4 mr-2" />
            {downloadLoading ? "Preparing..." : "Cash Close CSV"}
          </Button>
        </div>
      </div>

      {dailyError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {dailyError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-5">
          <h2 className="text-lg font-semibold text-gray-900">Cash Close</h2>
          <p className="text-sm text-gray-500">Payments in/out for {formatDate(date)}</p>
          <div className="mt-4 space-y-3 text-sm">
            {dailyLoading || !dailyCashClose ? (
              <Skeleton className="h-20" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span>Cash Net</span>
                  <span className="font-medium">
                    {formatCurrency(dailyCashClose.cash.net_cents)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Card Net</span>
                  <span className="font-medium">
                    {formatCurrency(dailyCashClose.card.net_cents)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Adjustments Net</span>
                  <span className="font-medium">
                    {formatCurrency(dailyCashClose.adjustments.net_cents)}
                  </span>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold text-gray-900">Settlement</h2>
          <p className="text-sm text-gray-500">Settled orders for the day.</p>
          <div className="mt-4 space-y-3 text-sm">
            {dailyLoading || !dailyCashClose ? (
              <Skeleton className="h-20" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span>Orders Settled</span>
                  <span className="font-medium">
                    {dailyCashClose.settlement.orders_settled_count}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Total Settled</span>
                  <span className="font-medium">
                    {formatCurrency(dailyCashClose.settlement.settled_total_cents)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Balance Due</span>
                  <span className="font-medium">
                    {formatCurrency(dailyCashClose.settlement.settled_balance_due_cents)}
                  </span>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold text-gray-900">Ops Summary</h2>
          <p className="text-sm text-gray-500">Operational alerts for the day.</p>
          <div className="mt-4 space-y-3 text-sm">
            {dailyLoading || !opsSummary ? (
              <Skeleton className="h-20" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span>Overdue</span>
                  <Badge variant="destructive">
                    {opsSummary.counts.orders_overdue}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Ready + Unpaid</span>
                  <Badge variant="secondary">
                    {opsSummary.counts.orders_ready_unpaid}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Picked up today</span>
                  <Badge variant="secondary">
                    {opsSummary.counts.orders_picked_up_today}
                  </Badge>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Workload Snapshot</h2>
            <p className="text-sm text-gray-500">Queue health for {formatDate(date)}.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant={range === "7d" ? "default" : "outline"}
              onClick={() => setRange("7d")}
            >
              Last 7 days
            </Button>
            <Button
              size="sm"
              variant={range === "30d" ? "default" : "outline"}
              onClick={() => setRange("30d")}
            >
              Last 30 days
            </Button>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {dailyLoading || !workload ? (
            Array.from({ length: 4 }).map((_, idx) => (
              <Skeleton key={idx} className="h-16" />
            ))
          ) : (
            <>
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Due Today</p>
                <p className="text-xl font-semibold">
                  {workload.counts.orders_due_today}
                </p>
              </div>
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Overdue</p>
                <p className="text-xl font-semibold">
                  {workload.counts.orders_overdue}
                </p>
              </div>
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Ready + Unpaid</p>
                <p className="text-xl font-semibold">
                  {workload.counts.orders_ready_unpaid}
                </p>
              </div>
              <div className="rounded-md border border-gray-200 p-3">
                <p className="text-xs text-gray-500">Completed, Unpicked</p>
                <p className="text-xl font-semibold">
                  {workload.counts.orders_completed_unpicked}
                </p>
              </div>
            </>
          )}
        </div>
      </Card>

      {rangeError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {rangeError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900">Revenue Summary</h2>
          <p className="text-sm text-gray-500">
            {range === "7d" ? "Last 7 days" : "Last 30 days"}
          </p>
          <div className="mt-4 space-y-3 text-sm">
            {rangeLoading || !revenueReport ? (
              <Skeleton className="h-24" />
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span>Orders settled</span>
                  <span className="font-medium">
                    {revenueReport.totals.orders_settled_count}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Settled total</span>
                  <span className="font-medium">
                    {formatCurrency(revenueReport.totals.settled_total_cents)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Cash net</span>
                  <span className="font-medium">
                    {formatCurrency(revenueReport.totals.cash_net_cents)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Card net</span>
                  <span className="font-medium">
                    {formatCurrency(revenueReport.totals.card_net_cents)}
                  </span>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900">Top Customers</h2>
          <p className="text-sm text-gray-500">
            {range === "7d" ? "Last 7 days" : "Last 30 days"}
          </p>
          <div className="mt-4 space-y-3 text-sm">
            {rangeLoading ? (
              <Skeleton className="h-24" />
            ) : topCustomers.length === 0 ? (
              <p className="text-gray-500">No customer activity yet.</p>
            ) : (
              topCustomers.map((row) => (
                <div key={row.customer.id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">
                      {row.customer.name || "Unknown"}
                    </p>
                    <p className="text-xs text-gray-500">{row.orders_count} orders</p>
                  </div>
                  <span className="font-medium">
                    {formatCurrency(row.settled_total_cents)}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900">Top Items</h2>
        <p className="text-sm text-gray-500">
          {range === "7d" ? "Last 7 days" : "Last 30 days"}
        </p>
        <div className="mt-4 space-y-3 text-sm">
          {rangeLoading ? (
            <Skeleton className="h-24" />
          ) : topItems.length === 0 ? (
            <p className="text-gray-500">No item activity yet.</p>
          ) : (
            topItems.map((item) => (
              <div key={item.item_id} className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-800">
                    {item.item__name || "Item"}
                  </p>
                  <p className="text-xs text-gray-500">{item.quantity} pieces</p>
                </div>
                <span className="font-medium">
                  {formatCurrency(item.revenue_cents)}
                </span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
