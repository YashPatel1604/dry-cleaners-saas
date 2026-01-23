import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiJson } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { formatCurrency, formatDateTime, statusTone } from "../lib/format";

type OrderCard = {
  order_id: number;
  pickup_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  customer: {
    id: number | null;
    name: string | null;
    phone: string | null;
    email: string | null;
  };
  money: {
    total_cents: number;
    net_paid_cents: number;
    balance_due_cents: number;
    change_due_cents: number;
  };
};

type OrderCardsResponse = {
  count: number;
  results: OrderCard[];
};

const STATUS_OPTIONS = ["ALL", "RECEIVED", "IN_PROGRESS", "READY", "COMPLETED", "PICKED_UP", "CANCELLED"];

export default function Orders(): JSX.Element {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<OrderCardsResponse>({ count: 0, results: [] });
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const params = useMemo(() => {
    const qs = new URLSearchParams({ limit: "20" });
    if (query) qs.set("q", query.trim());
    if (status && status !== "ALL") qs.set("status", status);
    return qs.toString();
  }, [query, status]);

  const fetchCards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiJson<OrderCardsResponse>(`/api/orders/cards/?${params}`);
      setData(resp);
    } catch {
      setError("Failed to load orders");
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const createOrder = async () => {
    setCreating(true);
    setError(null);
    try {
      const resp = await apiJson<{ id: number }>("/api/orders/", {
        method: "POST",
        body: { status: "RECEIVED" },
      });
      navigate(`/orders/${resp.id}`);
    } catch {
      setError("Could not create order");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
            Orders
          </div>
          <h1 className="text-3xl font-semibold">Active tickets</h1>
          <p className="text-sm text-muted-foreground">
            {loading ? "Loading..." : `${data.count} total orders`}
          </p>
        </div>
        <Button onClick={createOrder} disabled={creating}>
          {creating ? "Creating..." : "New order"}
        </Button>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <CardTitle>Search & filter</CardTitle>
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((value) => (
              <Button
                key={value}
                variant={status === value ? "default" : "outline"}
                onClick={() => setStatus(value)}
                size="sm"
              >
                {value}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            placeholder="Search by pickup ID or customer"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {error && <div className="text-sm text-red-600">{error}</div>}
        </CardContent>
      </Card>

      {!loading && data.results.length === 0 && (
        <Card className="glass-panel border-border/70">
          <CardContent className="p-6 text-sm text-muted-foreground">
            No orders found. Try a different search or create a new order.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {data.results.map((order) => (
          <Card
            key={order.order_id}
            className="glass-panel border-border/70 cursor-pointer transition hover:shadow-md"
            onClick={() => navigate(`/orders/${order.order_id}`)}
          >
            <CardContent className="p-5 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    Pickup #{order.pickup_id}
                  </div>
                  <div className="text-lg font-semibold">
                    {order.customer?.name ?? "Walk-in"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Opened {formatDateTime(order.created_at)}
                  </div>
                </div>
                <Badge variant={statusTone(order.status)}>{order.status}</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Total</div>
                  <div className="font-medium">{formatCurrency(order.money.total_cents)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Paid</div>
                  <div className="font-medium">{formatCurrency(order.money.net_paid_cents)}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted-foreground">Balance due</div>
                  <div className="font-semibold">{formatCurrency(order.money.balance_due_cents)}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
