import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, RefreshCw } from "lucide-react";

import { fetchOrderCards, type OrderCard } from "@/api/orders";
import {
  fetchDashboardSummary,
  fetchOrdersByStatus,
  type DashboardSummary,
  type OrdersByStatusRow,
} from "@/api/dashboard";
import {
  fetchTopCustomers,
  fetchTopItems,
  fetchWorkloadReport,
  type ReportItemSummary,
  type TopCustomer,
  type WorkloadReport,
} from "@/api/reports";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface DashboardSectionProps {
  onOpenOrders: (filters?: { status?: string; query?: string }) => void;
  onOpenDrop: () => void;
  onOpenCustomers: () => void;
  onOpenReports: () => void;
}

type RangeKey = "7d" | "30d";

const STATUS_LABELS: Record<string, string> = {
  RECEIVED: "Received",
  IN_PROGRESS: "In Progress",
  READY: "Ready",
  COMPLETED: "Completed",
  PICKED_UP: "Picked Up",
  CANCELLED: "Cancelled",
};

const STATUS_TO_FILTER: Record<string, string> = {
  RECEIVED: "in-progress",
  IN_PROGRESS: "in-progress",
  READY: "ready",
  COMPLETED: "picked-up",
  PICKED_UP: "picked-up",
  CANCELLED: "cancelled",
};

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

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

export function DashboardSection({
  onOpenOrders,
  onOpenDrop,
  onOpenCustomers,
  onOpenReports,
}: DashboardSectionProps) {
  const [range, setRange] = useState<RangeKey>("30d");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [workload, setWorkload] = useState<WorkloadReport | null>(null);
  const [statusRows, setStatusRows] = useState<OrdersByStatusRow[]>([]);
  const [recentOrders, setRecentOrders] = useState<OrderCard[]>([]);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [topItems, setTopItems] = useState<ReportItemSummary[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [baseLoading, setBaseLoading] = useState(true);
  const [topLoading, setTopLoading] = useState(true);
  const [baseError, setBaseError] = useState<string | null>(null);
  const [topError, setTopError] = useState<string | null>(null);

  const rangeDates = useMemo(() => {
    const end = new Date();
    const days = range === "7d" ? 6 : 29;
    const start = new Date();
    start.setDate(end.getDate() - days);
    return {
      start: toDateInput(start),
      end: toDateInput(end),
    };
  }, [range]);

  const statusMap = useMemo(() => {
    const map = new Map<string, number>();
    statusRows.forEach((row) => {
      map.set(row.status, row.count);
    });
    return map;
  }, [statusRows]);

  useEffect(() => {
    let isMounted = true;
    const loadBase = async () => {
      setBaseLoading(true);
      setBaseError(null);
      try {
        const [summaryRes, workloadRes, statusRes, recentRes] = await Promise.all([
          fetchDashboardSummary(),
          fetchWorkloadReport(),
          fetchOrdersByStatus(),
          fetchOrderCards({ limit: 6, offset: 0 }),
        ]);
        if (!isMounted) return;
        setSummary(summaryRes);
        setWorkload(workloadRes);
        setStatusRows(statusRes);
        setRecentOrders(recentRes.results);
      } catch (err) {
        if (!isMounted) return;
        setBaseError(err instanceof Error ? err.message : "Unable to load dashboard.");
      } finally {
        if (isMounted) setBaseLoading(false);
      }
    };

    loadBase();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  useEffect(() => {
    let isMounted = true;
    const loadTopLists = async () => {
      setTopLoading(true);
      setTopError(null);
      try {
        const [customersRes, itemsRes] = await Promise.all([
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
        setTopCustomers(customersRes.results || []);
        setTopItems(itemsRes || []);
      } catch (err) {
        if (!isMounted) return;
        setTopError(err instanceof Error ? err.message : "Unable to load insights.");
      } finally {
        if (isMounted) setTopLoading(false);
      }
    };

    loadTopLists();
    return () => {
      isMounted = false;
    };
  }, [rangeDates, refreshKey]);

  const liveQueueCards = [
    {
      label: "Due Today",
      value: workload?.counts.orders_due_today ?? null,
      age: workload?.avg_age_hours.orders_due_today,
    },
    {
      label: "Overdue",
      value: workload?.counts.orders_overdue ?? null,
      age: workload?.avg_age_hours.orders_overdue,
    },
    {
      label: "Ready + Unpaid",
      value: workload?.counts.orders_ready_unpaid ?? null,
      age: workload?.avg_age_hours.orders_ready_unpaid,
    },
    {
      label: "Completed, Unpicked",
      value: workload?.counts.orders_completed_unpicked ?? null,
      age: workload?.avg_age_hours.orders_completed_unpicked,
    },
  ];

  return (
    <div className="max-w-6xl space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">
            Live workload, exceptions, and quick insights.
          </p>
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
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setRefreshKey((prev) => prev + 1);
            }}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {baseError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {baseError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {liveQueueCards.map((card) => (
          <Card key={card.label} className="p-4">
            {baseLoading ? (
              <Skeleton className="h-20" />
            ) : (
              <>
                <p className="text-sm text-gray-500">{card.label}</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {card.value ?? "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Avg age {card.age ?? 0}h
                </p>
              </>
            )}
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Workload by Stage
              </h2>
              <p className="text-sm text-gray-500">Current status distribution.</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => onOpenOrders()}>
              View Orders
            </Button>
          </div>
          <div className="mt-4 space-y-3">
            {baseLoading
              ? Array.from({ length: 5 }).map((_, idx) => (
                  <Skeleton key={idx} className="h-6" />
                ))
              : ["RECEIVED", "IN_PROGRESS", "READY", "COMPLETED", "PICKED_UP"].map(
                  (status) => (
                    <div
                      key={status}
                      className="flex items-center justify-between text-sm text-gray-700"
                    >
                      <span>{STATUS_LABELS[status]}</span>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {statusMap.get(status) ?? 0}
                        </Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            onOpenOrders({ status: STATUS_TO_FILTER[status] })
                          }
                        >
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )
                )}
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Exceptions</h2>
              <p className="text-sm text-gray-500">Items needing attention.</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => onOpenOrders()}>
              View Orders
            </Button>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            {baseLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} className="h-6" />
              ))
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span>Overdue</span>
                  <Badge variant="destructive">
                    {workload?.counts.orders_overdue ?? 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Ready but unpaid</span>
                  <Badge variant="secondary">
                    {workload?.counts.orders_ready_unpaid ?? 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Completed, not picked up</span>
                  <Badge variant="secondary">
                    {workload?.counts.orders_completed_unpicked ?? 0}
                  </Badge>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Top Customers</h2>
              <p className="text-sm text-gray-500">
                {range === "7d" ? "Last 7 days" : "Last 30 days"}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={onOpenCustomers}>
              View Customers
            </Button>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            {topLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} className="h-6" />
              ))
            ) : topError ? (
              <div className="text-red-600 text-xs">{topError}</div>
            ) : topCustomers.length === 0 ? (
              <p className="text-gray-500">No customer activity yet.</p>
            ) : (
              topCustomers.map((row) => (
                <div key={row.customer.id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">
                      {row.customer.name || "Unknown"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {row.orders_count} orders
                    </p>
                  </div>
                  <span className="font-medium text-gray-900">
                    {formatCurrency(row.settled_total_cents)}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Top Items</h2>
              <p className="text-sm text-gray-500">
                {range === "7d" ? "Last 7 days" : "Last 30 days"}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={onOpenDrop}>
              Start Drop-Off
            </Button>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            {topLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} className="h-6" />
              ))
            ) : topError ? (
              <div className="text-red-600 text-xs">{topError}</div>
            ) : topItems.length === 0 ? (
              <p className="text-gray-500">No item data yet.</p>
            ) : (
              topItems.map((item) => (
                <div key={item.item_id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">
                      {item.item__name || "Item"}
                    </p>
                    <p className="text-xs text-gray-500">{item.quantity} pieces</p>
                  </div>
                  <span className="font-medium text-gray-900">
                    {formatCurrency(item.revenue_cents)}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Recent Activity
              </h2>
              <p className="text-sm text-gray-500">Latest orders updated.</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => onOpenOrders()}>
              View Orders
            </Button>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            {baseLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <Skeleton key={idx} className="h-6" />
              ))
            ) : recentOrders.length === 0 ? (
              <p className="text-gray-500">No orders yet.</p>
            ) : (
              recentOrders.map((order) => (
                <div key={order.order_id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">
                      #{order.order_id} · {order.customer?.name || "Walk-in"}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDateTime(order.updated_at || order.created_at)}
                    </p>
                  </div>
                  <Badge variant={order.status === "CANCELLED" ? "destructive" : "secondary"}>
                    {STATUS_LABELS[order.status] || order.status}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="p-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
            <p className="text-sm text-gray-500">Jump to common tasks.</p>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Button onClick={onOpenDrop}>Start Drop-Off</Button>
            <Button variant="outline" onClick={() => onOpenOrders()}>
              View Orders
            </Button>
            <Button variant="outline" onClick={onOpenCustomers}>
              Search Customers
            </Button>
            <Button variant="outline" onClick={onOpenReports}>
              Open Reports
            </Button>
          </div>
          {summary && (
            <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Orders today</span>
                <span className="font-medium text-gray-900">
                  {summary.orders_today}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-gray-500">Value today</span>
                <span className="font-medium text-gray-900">
                  ${summary.orders_value_today}
                </span>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-gray-500">Collected today</span>
                <span className="font-medium text-gray-900">
                  ${summary.collected_today}
                </span>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
