import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { formatCurrency, formatDate } from "../lib/format";

type SummaryResponse = {
  date: string;
  orders: {
    created_count: number;
    settled_count: number;
    open_count: number;
    unpaid_count: number;
  };
  money: {
    gross_sales_cents: number;
    discounts_cents: number;
    tax_cents: number;
    net_sales_cents: number;
    net_paid_cents: number;
    balance_due_cents: number;
    change_due_cents: number;
  };
  payments: {
    by_method: Array<{ method: string; amount_cents: number }>;
  };
};

type RangeRow = {
  date: string;
  orders_created: number;
  orders_settled: number;
  net_sales_cents: number;
  net_paid_cents: number;
  balance_due_cents: number;
};

type RangeResponse = {
  start: string;
  end: string;
  series: RangeRow[];
};

type UnpaidRow = {
  order_id: number;
  customer_name: string | null;
  status: string;
  total_cents: number;
  net_paid_cents: number;
  balance_due_cents: number;
  created_at: string;
};

type UnpaidResponse = {
  count: number;
  results: UnpaidRow[];
};

export default function Reports(): JSX.Element {
  const today = new Date().toISOString().slice(0, 10);
  const [summaryDate, setSummaryDate] = useState(today);
  const [rangeStart, setRangeStart] = useState(today);
  const [rangeEnd, setRangeEnd] = useState(today);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [range, setRange] = useState<RangeResponse | null>(null);
  const [unpaid, setUnpaid] = useState<UnpaidResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = async () => {
    try {
      const resp = await apiJson<SummaryResponse>(
        `/api/tenant/reports/summary/?date=${summaryDate}`
      );
      setSummary(resp);
    } catch {
      setError("Failed to load summary");
    }
  };

  const loadRange = async () => {
    try {
      const resp = await apiJson<RangeResponse>(
        `/api/tenant/reports/range/?start=${rangeStart}&end=${rangeEnd}`
      );
      setRange(resp);
    } catch {
      setError("Failed to load range");
    }
  };

  const loadUnpaid = async () => {
    try {
      const resp = await apiJson<UnpaidResponse>("/api/tenant/reports/unpaid/?limit=50&offset=0");
      setUnpaid(resp);
    } catch {
      setError("Failed to load unpaid report");
    }
  };

  useEffect(() => {
    loadSummary();
    loadRange();
    loadUnpaid();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Reports
        </div>
        <h1 className="text-3xl font-semibold">Daily insights</h1>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <Card className="glass-panel border-border/70">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <CardTitle>Summary</CardTitle>
          <div className="flex items-center gap-3">
            <Input type="date" value={summaryDate} onChange={(e) => setSummaryDate(e.target.value)} />
            <Button onClick={loadSummary}>Refresh</Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="text-xs text-muted-foreground">Orders created</div>
            <div className="text-2xl font-semibold">{summary?.orders.created_count ?? 0}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Orders settled</div>
            <div className="text-2xl font-semibold">{summary?.orders.settled_count ?? 0}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Open orders</div>
            <div className="text-2xl font-semibold">{summary?.orders.open_count ?? 0}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Unpaid</div>
            <div className="text-2xl font-semibold">{summary?.orders.unpaid_count ?? 0}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Net sales</div>
            <div className="text-xl font-semibold">
              {formatCurrency(summary?.money.net_sales_cents ?? 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Net paid</div>
            <div className="text-xl font-semibold">
              {formatCurrency(summary?.money.net_paid_cents ?? 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Balance due</div>
            <div className="text-xl font-semibold">
              {formatCurrency(summary?.money.balance_due_cents ?? 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Change due</div>
            <div className="text-xl font-semibold">
              {formatCurrency(summary?.money.change_due_cents ?? 0)}
            </div>
          </div>
        </CardContent>
        {summary && (
          <CardContent className="pt-0">
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Payments by method
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {summary.payments.by_method.map((row) => (
                <Badge key={row.method} variant="outline">
                  {row.method} {formatCurrency(row.amount_cents)}
                </Badge>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <CardTitle>Range view</CardTitle>
          <div className="flex flex-wrap items-center gap-3">
            <Input type="date" value={rangeStart} onChange={(e) => setRangeStart(e.target.value)} />
            <Input type="date" value={rangeEnd} onChange={(e) => setRangeEnd(e.target.value)} />
            <Button variant="secondary" onClick={loadRange}>
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {range?.series?.map((row) => (
            <div key={row.date} className="flex flex-wrap items-center justify-between gap-3">
              <div className="font-medium">{formatDate(row.date)}</div>
              <div className="text-muted-foreground">Created {row.orders_created}</div>
              <div className="text-muted-foreground">Settled {row.orders_settled}</div>
              <div>{formatCurrency(row.net_sales_cents)}</div>
              <div>{formatCurrency(row.net_paid_cents)}</div>
              <div>{formatCurrency(row.balance_due_cents)}</div>
            </div>
          ))}
          {!range?.series?.length && (
            <div className="text-muted-foreground">No data for this range.</div>
          )}
        </CardContent>
      </Card>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Unpaid orders</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {unpaid?.results?.map((row) => (
            <div key={row.order_id} className="rounded-xl border border-border bg-white/70 px-3 py-2">
              <div className="flex items-center justify-between">
                <div className="font-medium">
                  Order #{row.order_id} · {row.customer_name || "Walk-in"}
                </div>
                <div>{formatCurrency(row.balance_due_cents)}</div>
              </div>
              <div className="text-xs text-muted-foreground">
                {row.status} · {formatDate(row.created_at)}
              </div>
            </div>
          ))}
          {!unpaid?.results?.length && (
            <div className="text-muted-foreground">No unpaid orders.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
