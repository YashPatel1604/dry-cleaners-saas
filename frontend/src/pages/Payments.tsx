import React, { useEffect, useState } from "react";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { formatCurrency, formatDateTime } from "../lib/format";

type Payment = {
  id: number;
  order: number;
  method: string;
  status: string;
  direction: string;
  amount_cents: number;
  reference: string;
  note: string;
  created_at: string;
};

type Adjustment = {
  id: number;
  order: number;
  kind: string;
  status: string;
  direction: string;
  amount_cents: number;
  reference: string | null;
  note: string;
  created_at: string;
};

export default function Payments(): JSX.Element {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [orderId, setOrderId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("CASH");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [payData, adjData] = await Promise.all([
        apiJson<Payment[]>("/api/payments/"),
        apiJson<Adjustment[]>("/api/adjustments/"),
      ]);
      setPayments(payData);
      setAdjustments(adjData);
    } catch {
      setError("Unable to load payments");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createPayment = async () => {
    setError(null);
    const cents = parseInt(amount || "0", 10);
    if (!orderId || !cents) return;
    try {
      await apiJson("/api/payments/", {
        method: "POST",
        body: {
          order: Number(orderId),
          amount_cents: cents,
          method,
          reference,
          note,
        },
      });
      setOrderId("");
      setAmount("");
      setReference("");
      setNote("");
      await load();
    } catch {
      setError("Failed to create payment");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
          Payments
        </div>
        <h1 className="text-3xl font-semibold">Ledger activity</h1>
      </div>

      <Card className="glass-panel border-border/70">
        <CardHeader>
          <CardTitle>Create payment</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_1fr_auto]">
          <Input placeholder="Order ID" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
          <Input placeholder="Amount (cents)" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <select
            className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            <option value="CASH">CASH</option>
            <option value="CARD">CARD</option>
            <option value="ONLINE">ONLINE</option>
            <option value="OTHER">OTHER</option>
          </select>
          <Input
            placeholder="Reference"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
          <Button onClick={createPayment}>Post</Button>
        </CardContent>
        <CardContent className="pt-0">
          <Input placeholder="Note" value={note} onChange={(e) => setNote(e.target.value)} />
        </CardContent>
        {error && <div className="px-6 pb-4 text-sm text-red-600">{error}</div>}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Payments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {payments.map((p) => (
              <div
                key={p.id}
                className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">
                    Order #{p.order} · {p.method}
                  </div>
                  <div>{formatCurrency(p.amount_cents)}</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {p.direction} · {p.status} · {formatDateTime(p.created_at)}
                </div>
              </div>
            ))}
            {payments.length === 0 && (
              <div className="text-sm text-muted-foreground">No payments yet.</div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Adjustments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {adjustments.map((a) => (
              <div
                key={a.id}
                className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">
                    Order #{a.order} · {a.kind}
                  </div>
                  <div>{formatCurrency(a.amount_cents)}</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {a.direction} · {a.status} · {formatDateTime(a.created_at)}
                </div>
              </div>
            ))}
            {adjustments.length === 0 && (
              <div className="text-sm text-muted-foreground">No adjustments yet.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
