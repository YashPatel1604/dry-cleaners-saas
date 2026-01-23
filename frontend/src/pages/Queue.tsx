import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiJson } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { formatCurrency, formatDateTime, statusTone } from "../lib/format";

type Order = {
  id: number;
  status: string;
  created_at: string;
  due_at: string | null;
  total_cents: number;
  paid_cents: number;
  customer_name?: string | null;
};

const STATUS_OPTIONS = ["CREATED", "IN_PROGRESS", "READY", "COMPLETED", "PICKED_UP", "CANCELLED"];

export default function Queue(): JSX.Element {
  const navigate = useNavigate();
  const [status, setStatus] = useState("READY");
  const [readyUnpaid, setReadyUnpaid] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadQueue = async () => {
    setError(null);
    try {
      const qs = new URLSearchParams({ status });
      if (readyUnpaid) qs.set("ready_unpaid", "1");
      const resp = await apiJson<Order[]>(`/api/orders/queue/?${qs.toString()}`);
      setOrders(resp);
    } catch {
      setError("Failed to load queue");
    }
  };

  useEffect(() => {
    loadQueue();
  }, [status, readyUnpaid]);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Queue
        </div>
        <h1 className="text-3xl font-semibold">Production flow</h1>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <CardTitle>Filters</CardTitle>
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((value) => (
              <Button
                key={value}
                variant={status === value ? "default" : "outline"}
                size="sm"
                onClick={() => setStatus(value)}
              >
                {value}
              </Button>
            ))}
            <Button
              variant={readyUnpaid ? "secondary" : "outline"}
              size="sm"
              onClick={() => setReadyUnpaid(!readyUnpaid)}
            >
              Ready unpaid only
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {error && <div className="text-sm text-red-600">{error}</div>}
          {orders.map((order) => (
            <div
              key={order.id}
              className="rounded-xl border border-border bg-white/70 px-3 py-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium">Order #{order.id}</div>
                  <div className="text-xs text-muted-foreground">
                    {order.customer_name || "Walk-in"} · {formatDateTime(order.created_at)}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={statusTone(order.status)}>{order.status}</Badge>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">Total</div>
                    <div className="font-semibold">{formatCurrency(order.total_cents)}</div>
                  </div>
                  <Button variant="outline" onClick={() => navigate(`/orders/${order.id}`)}>
                    Open
                  </Button>
                </div>
              </div>
            </div>
          ))}
          {orders.length === 0 && (
            <div className="text-sm text-muted-foreground">No orders in this queue.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
