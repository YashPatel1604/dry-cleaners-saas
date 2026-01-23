import React, { useEffect, useMemo, useState } from "react";

import { apiJson } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatCurrency, formatDate } from "../lib/format";

type DashboardSummary = {
  orders_today: number;
  orders_value_today: string;
  collected_today: string;
  in_progress: number;
  ready: number;
  overdue: number;
};

type RevenueRow = {
  date: string;
  orders: number;
  orders_value: string;
  collected: string;
};

type StatusRow = {
  status: string;
  count: number;
};

function parseMoneyString(value: string | null | undefined): number {
  if (!value) return 0;
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return 0;
  return parsed;
}

export default function Dashboard(): JSX.Element {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [revenue, setRevenue] = useState<RevenueRow[]>([]);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<"7d" | "30d">("7d");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([
      apiJson<DashboardSummary>("/api/dashboard/summary/"),
      apiJson<RevenueRow[]>(`/api/dashboard/revenue/?range=${range}`),
      apiJson<StatusRow[]>("/api/dashboard/orders-by-status/"),
    ])
      .then(([summaryData, revenueData, statusData]) => {
        if (!alive) return;
        setSummary(summaryData);
        setRevenue(revenueData);
        setStatusRows(statusData);
      })
      .catch(() => {
        if (!alive) return;
        setSummary(null);
        setRevenue([]);
        setStatusRows([]);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [range]);

  const maxRevenue = useMemo(() => {
    return revenue.reduce((max, row) => Math.max(max, parseMoneyString(row.orders_value)), 0);
  }, [revenue]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
            Today
          </div>
          <h1 className="text-3xl font-semibold">Operations Overview</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant={range === "7d" ? "default" : "outline"} onClick={() => setRange("7d")}>
            Last 7 days
          </Button>
          <Button variant={range === "30d" ? "default" : "outline"} onClick={() => setRange("30d")}>
            Last 30 days
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass-panel border-border/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-[0.25em] text-muted-foreground">
              Orders today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">{summary?.orders_today ?? 0}</div>
            <div className="text-sm text-muted-foreground">
              Value {summary?.orders_value_today ?? "0.00"}
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel border-border/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-[0.25em] text-muted-foreground">
              Collected today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold">
              ${summary?.collected_today ?? "0.00"}
            </div>
            <div className="text-sm text-muted-foreground">
              Across all methods
            </div>
          </CardContent>
        </Card>
        <Card className="glass-panel border-border/70">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm uppercase tracking-[0.25em] text-muted-foreground">
              Workload
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>In progress</span>
              <Badge variant="warning">{summary?.in_progress ?? 0}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Ready</span>
              <Badge variant="success">{summary?.ready ?? 0}</Badge>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span>Overdue</span>
              <Badge variant="danger">{summary?.overdue ?? 0}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Revenue trend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading && <div className="text-sm text-muted-foreground">Loading…</div>}
            {!loading && revenue.length === 0 && (
              <div className="text-sm text-muted-foreground">No revenue data yet.</div>
            )}
            {revenue.map((row) => {
              const widthPct = maxRevenue > 0 ? (parseMoneyString(row.orders_value) / maxRevenue) * 100 : 0;
              return (
                <div key={row.date} className="space-y-1">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{formatDate(row.date)}</span>
                    <span>
                      Orders {row.orders} · ${row.orders_value} / ${row.collected}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{ width: `${Math.max(widthPct, 6)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Status mix</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {statusRows.length === 0 && (
              <div className="text-sm text-muted-foreground">No orders yet.</div>
            )}
            {statusRows.map((row) => (
              <div key={row.status} className="flex items-center justify-between text-sm">
                <span>{row.status}</span>
                <Badge variant="outline">{row.count}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button asChild>
            <a href="/orders">View orders</a>
          </Button>
          <Button variant="secondary" asChild>
            <a href="/customers">Find a customer</a>
          </Button>
          <Button variant="outline" asChild>
            <a href="/reports">Run reports</a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
