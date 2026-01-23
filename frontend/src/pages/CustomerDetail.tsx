import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiJson } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { formatCurrency, formatDateTime } from "../lib/format";

type Customer = {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

type CustomerOrder = {
  id: number;
  status: string;
  created_at: string;
  due_at: string | null;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  paid_cents: number;
  settled_at: string | null;
  notes: string;
};

type OrdersResponse = {
  count: number;
  results: CustomerOrder[];
};

export default function CustomerDetail(): JSX.Element {
  const { id } = useParams();
  const navigate = useNavigate();
  const customerId = Number(id);

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [orders, setOrders] = useState<OrdersResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!customerId) return;
    Promise.all([
      apiJson<Customer>(`/api/tenant/customers/${customerId}/`),
      apiJson<OrdersResponse>(`/api/tenant/customers/${customerId}/orders/`),
    ])
      .then(([customerData, orderData]) => {
        setCustomer(customerData);
        setOrders(orderData);
      })
      .catch(() => setError("Unable to load customer"));
  }, [customerId]);

  const updateCustomer = async () => {
    if (!customer) return;
    setSaving(true);
    setError(null);
    try {
      const resp = await apiJson<Customer>(`/api/tenant/customers/${customerId}/`, {
        method: "PATCH",
        body: {
          name: customer.name,
          phone: customer.phone,
          email: customer.email,
          notes: customer.notes,
        },
      });
      setCustomer(resp);
    } catch {
      setError("Failed to update customer");
    } finally {
      setSaving(false);
    }
  };

  const deleteCustomer = async () => {
    if (!customerId) return;
    const confirmed = window.confirm("Delete this customer? This cannot be undone.");
    if (!confirmed) return;
    await apiJson(`/api/tenant/customers/${customerId}/`, { method: "DELETE" });
    navigate("/customers");
  };

  const createOrder = async () => {
    if (!customerId) return;
    const resp = await apiJson<{ order_id: number }>(`/api/tenant/customers/${customerId}/orders/`, {
      method: "POST",
      body: {},
    });
    navigate(`/orders/${resp.order_id}`);
  };

  if (!customer) {
    return (
      <Card>
        <CardContent className="p-6">{error || "Loading customer..."}</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground/70">
            Customer
          </div>
          <h1 className="text-3xl font-semibold">{customer.name}</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={createOrder}>
            Create order
          </Button>
          <Button variant="outline" onClick={() => navigate("/customers")}>
            Back
          </Button>
        </div>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              value={customer.name}
              onChange={(e) => setCustomer({ ...customer, name: e.target.value })}
            />
            <Input
              placeholder="Phone"
              value={customer.phone || ""}
              onChange={(e) => setCustomer({ ...customer, phone: e.target.value })}
            />
            <Input
              placeholder="Email"
              value={customer.email || ""}
              onChange={(e) => setCustomer({ ...customer, email: e.target.value })}
            />
            <Textarea
              placeholder="Notes"
              value={customer.notes || ""}
              onChange={(e) => setCustomer({ ...customer, notes: e.target.value })}
            />
            <div className="flex gap-2">
              <Button onClick={updateCustomer} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </Button>
              <Button variant="outline" onClick={deleteCustomer}>
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-panel border-border/70">
          <CardHeader>
            <CardTitle>Orders</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {orders?.results?.length ? (
              orders.results.map((order) => (
                <button
                  key={order.id}
                  className="w-full rounded-xl border border-border bg-white/70 px-3 py-3 text-left transition hover:bg-white"
                  onClick={() => navigate(`/orders/${order.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">Order #{order.id}</div>
                      <div className="text-xs text-muted-foreground">
                        {order.status} · {formatDateTime(order.created_at)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">Total</div>
                      <div className="font-semibold">{formatCurrency(order.total_cents)}</div>
                    </div>
                  </div>
                </button>
              ))
            ) : (
              <div className="text-sm text-muted-foreground">No orders yet.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
